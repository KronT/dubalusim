# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team and Sentry Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:copyright: Copyright (c) 2010-2012 by the Sentry Team.
:license: See LICENSE for more details.

"""
from __future__ import absolute_import, print_function

import sys
import time
import atexit
import threading
from Queue import Queue
from functools import wraps

import logging
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

_worker = None


class AsyncWorker(object):
    _terminator = object()

    def __init__(self, shutdown_timeout=DEFAULT_TIMEOUT, num_threads=10):
        self._queue = Queue(-1)
        self._lock = threading.Lock()
        self._threads = None
        self.num_threads = num_threads
        self.options = {
            'shutdown_timeout': shutdown_timeout,
        }
        self.start()

    def main_thread_terminated(self):
        self._lock.acquire()
        try:
            if not self._threads:
                # thread not started or already stopped - nothing to do
                return

            # wake the processing thread up
            for _ in range(self.num_threads):
                self._queue.put_nowait(self._terminator)

            timeout = self.options['shutdown_timeout']

            # wait briefly, initially
            initial_timeout = 0.1
            if timeout < initial_timeout:
                initial_timeout = timeout

            if not self._timed_queue_join(self._queue, initial_timeout):
                # if that didn't work, wait a bit longer
                # NB that size is an approximation, because other threads may
                # add or remove items
                old_size = self._queue.qsize()

                print("Attempting to complete %i pending async tasks" % old_size, file=sys.stderr)
                print("Waiting up to %s idle seconds" % timeout, file=sys.stderr)
                print("Press Ctrl-C to quit", file=sys.stderr)

                while not self._timed_queue_join(self._queue, timeout - initial_timeout):
                    new_size = self._queue.qsize()
                    if old_size == new_size:
                        print("Aborted!", end="", file=sys.stderr)
                        break
                    old_size = new_size
                    print("%s " % new_size, end="", file=sys.stderr)

                print(file=sys.stderr)

            self._threads = None

        finally:
            self._lock.release()

    def _timed_queue_join(self, queue, timeout):
        """
        implementation of Queue.join which takes a 'timeout' argument

        returns true on success, false on timeout
        """
        deadline = time.time() + timeout

        queue.all_tasks_done.acquire()
        try:
            while queue.unfinished_tasks:
                delay = deadline - time.time()
                if delay <= 0:
                    # timed out
                    return False

                queue.all_tasks_done.wait(timeout=delay)

            return True

        finally:
            queue.all_tasks_done.release()

    def start(self):
        """
        Starts the task thread.
        """
        self._lock.acquire()
        try:
            if not self._threads:
                self._threads = Queue(self.num_threads)
                for idx in range(self.num_threads):
                    thread = threading.Thread(
                        name="AsyncThread%s" % (idx + 1),
                        target=self._target,
                        args=(self._threads,),
                    )
                    thread.setDaemon(True)
                    thread.start()
                    self._threads.put(thread)
        finally:
            self._lock.release()
            atexit.register(self.main_thread_terminated)

    def stop(self, timeout=None):
        """
        Stops the task thread. Synchronous!
        """
        self._lock.acquire()
        try:
            if self._threads:
                for _ in range(self.num_threads):
                    self._queue.put_nowait(self._terminator)
                self._timed_queue_join(self._threads, timeout=timeout)
                self._threads = None
        finally:
            self._lock.release()

    def queue(self, func, args, kwargs, name, log_exceptions):
        self._queue.put_nowait((func, args, kwargs, name, log_exceptions))

    def _target(self, threads):
        try:
            while True:
                record = self._queue.get()
                try:
                    if record is self._terminator:
                        break
                    func, args, kwargs, name, log_exceptions = record
                    if not name:
                        name = func.__name__
                    try:
                        try:
                            func(*args, **kwargs)
                        except Exception:
                            if log_exceptions:
                                raise
                    except Exception as e:
                        logger.error('Async job failed - %s(): %s', name, e, exc_info=True)
                finally:
                    self._queue.task_done()
                time.sleep(0)
        except Exception as e:
            logger.error('AsyncThread worker died unexpectedly: %s', e, exc_info=True)
            raise
        finally:
            threads.task_done()


def async(func=None, name=None, log_exceptions=True):
    def _async(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            global _worker
            if _worker is None:
                _worker = AsyncWorker()
            _worker.queue(func, args, kwargs, name, log_exceptions)
        return wrapped
    if callable(func):
        return _async(func)
    return _async
