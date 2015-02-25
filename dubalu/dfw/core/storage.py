# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import

import os
import warnings
import threading
from collections import deque

from django.conf import settings
from django.utils._os import abspathu
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage, Storage, FileSystemStorage as DjangoFileSystemStorage
from django.core.signals import request_finished, request_started

from async import async


def _expand_path_nodes(path, niddle):
    nodes = path.split(os.path.sep, niddle + 1)
    prev_nodes = nodes[:niddle]
    nodes = nodes[niddle:]
    dirname = nodes[0] if len(nodes) > 1 else ''
    dirname_len = len(dirname)
    if not dirname_len:
        return prev_nodes + nodes
    elif dirname_len == 1:
        return prev_nodes + ['1' + dirname] + nodes
    elif dirname_len <= 3:
        return prev_nodes + ['3' + dirname[-1]] + nodes
    elif dirname_len <= 6:
        return prev_nodes + ['6' + dirname[:2], dirname[-2:]] + nodes
    else:
        return prev_nodes + ['A' + dirname[:3], dirname[3:6], dirname[-3:]] + nodes


def expand_path(path, niddle=1):
    """
    This is the expansion functions for an internal user storage.

    What is / What is not

    - It can be used as a key-value database
    - By design/convenience keys are not literal, they are normalized as unix's file-paths
    - In the current backend any value corresponds to a filesystem entry
    - Currently, any replication technique should be applied over the filesystem

    - It is self indexed by directory structure
        + A key is a path composed of nodes /node1/node2/.../node-file
        + A key's path is a virtual path
        + This virtual path is mapped to some-root-directory/indexing-function(node1)/node2/.../node-file
          The algorithm is based on the length and implemented in _expand_path_nodes().

    """
    return os.path.join(*_expand_path_nodes(path, niddle))


class FileSystemStorage(DjangoFileSystemStorage):
    """
    Standard filesystem storage

    This class is almost exactly the same as django's, the only difference is in
    that this allows for ``MEDIA_URL`` and ``MEDIA_ROOT`` to be volatile.

    To use, add the following to ``settings``:
        DEFAULT_FILE_STORAGE = 'dfw.core.storage.FileSystemStorage'

    """
    STORAGE_ROOT_NAME = 'MEDIA_ROOT'
    STORAGE_URL_NAME = 'MEDIA_URL'

    def __init__(self, location=None, base_url=None):
        self._base_location = location
        self._base_url = base_url

    @property
    def base_url(self):
        if self._base_url is None:
            return getattr(settings, self.STORAGE_URL_NAME)
        else:
            return self._base_url

    @property
    def base_location(self):
        if self._base_location is None:
            return getattr(settings, self.STORAGE_ROOT_NAME)
        else:
            self._base_location

    @property
    def location(self):
        return abspathu(self.base_location)


class StaticFilesStorage(FileSystemStorage):
    """
    Standard file system storage for static files.

    The defaults for ``location`` and ``base_url`` are
    ``STATIC_ROOT`` and ``STATIC_URL``.

    This class is almost exactly the same as django's, the only difference is in
    that this allows for ``STATIC_ROOT`` and ``STATIC_URL`` to be volatile.

    To use, add the following to ``settings``:
        STATICFILES_STORAGE = 'dfw.core.storage.StaticFilesStorage'

    """
    STORAGE_ROOT_NAME = 'STATIC_ROOT'
    STORAGE_URL_NAME = 'STATIC_URL'

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("You're using the staticfiles app "
                                       "without having set the STATIC_ROOT "
                                       "setting to a filesystem path.")
        return super(StaticFilesStorage, self).path(name)


deferred = threading.local()


def deferred_setup(**kwargs):
    deferred.deletes = deque()
request_started.connect(deferred_setup)


def deferred_process(**kwargs):
    if hasattr(deferred, 'deletes'):
        queue = deferred.deletes
        del deferred.deletes
        while True:
            try:
                self, local_settings, storage, name = queue.pop()
            except IndexError:
                break
            self.async_delete(local_settings, storage, name)
request_finished.connect(deferred_process)


class QueuedStorage(Storage):
    """
    This is the Queued Storage class, child classes could add
    LOCAL_STORAGE and REMOTE_STORAGE for default storages.

    """
    LOCAL_STORAGE = FileSystemStorage('/tmp/queued_storage')
    REMOTE_STORAGE = default_storage

    def __init__(self, local=None, remote=None):
        self.local = self.LOCAL_STORAGE if local is None else local
        self.remote = self.REMOTE_STORAGE if remote is None else remote

    def _get_storage(self, name):
        if self.local.exists(name):
            return self.local
        else:
            return self.remote

    def _get_deferred_queue(self):
        try:
            return deferred.deletes
        except AttributeError:
            return None

    def deferred_delete(self, local_settings, storage, name, queue=None):
        """
        Defers the delete until the end of the request.

        """
        if queue is None:
            queue = self._get_deferred_queue()
        if queue is None:
            self.async_delete(local_settings, storage, name)
        else:
            queue.append((self, local_settings, storage, name))

    @async()
    def async_transfer(self, local_settings, name, queue):
        """
        Saves to the remote storage (also, removing the local copy)

        """
        settings.clear(local_settings)
        try:
            with self.local.open(name) as content:
                if self.remote.exists(name):
                    self.remote.delete(name)
                self.remote.save(name, content)
            self.deferred_delete(local_settings, self.local, name, queue)
        finally:
            settings.clear()

    @async()
    def async_delete(self, local_settings, storage, name, log_exceptions=True):
        settings.clear(local_settings)
        try:
            try:
                storage.delete(name)
            except Exception:
                if log_exceptions:
                    raise
        finally:
            settings.clear()

    def _open(self, name, mode='rb'):
        return self._get_storage(name).open(name, mode=mode)

    def _get_settings(self):
        """
        Method to return all settings the storage depends on (for passing to the async thread)

        """
        LOCAL_STORAGE_ROOT_NAME = getattr(self.local, 'STORAGE_ROOT_NAME', 'MEDIA_ROOT')
        LOCAL_STORAGE_URL_NAME = getattr(self.local, 'STORAGE_URL_NAME', 'MEDIA_URL')
        REMOTE_STORAGE_ROOT_NAME = getattr(self.remote, 'STORAGE_ROOT_NAME', 'MEDIA_ROOT')
        REMOTE_STORAGE_URL_NAME = getattr(self.remote, 'STORAGE_URL_NAME', 'MEDIA_URL')
        return {
            LOCAL_STORAGE_ROOT_NAME: getattr(settings, LOCAL_STORAGE_ROOT_NAME),
            LOCAL_STORAGE_URL_NAME: getattr(settings, LOCAL_STORAGE_URL_NAME),
            REMOTE_STORAGE_ROOT_NAME: getattr(settings, REMOTE_STORAGE_ROOT_NAME),
            REMOTE_STORAGE_URL_NAME: getattr(settings, REMOTE_STORAGE_URL_NAME),
        }

    def _save(self, name, content):
        ret = self.local.save(name, content)
        self.async_transfer(self._get_settings(), name, self._get_deferred_queue())
        return ret

    def path(self, name):
        if self.local.exists(name):
            path = self.local.path(name)
        else:
            if isinstance(self.remote, DjangoFileSystemStorage):
                path = self.remote.path(name)
            else:
                warnings.warn("Expensive path is being used!", stacklevel=2)
                with self.remote.open(name) as content:
                    self.local.save(name, content)
                path = self.local.path(name)
                local_settings = self._get_settings()
                self.deferred_delete(local_settings, self.local, name)
        return path

    def delete(self, name):
        try:
            self.local.delete(name)
            log_exceptions = False
        except IOError:
            log_exceptions = True
        self.async_delete(self._get_settings(), self.remote, name, log_exceptions)

    def exists(self, name):
        if self.local.exists(name):
            return True
        try:
            return self.remote.exists(name)
        except Exception:
            pass
        return False

    def listdir(self, path):
        directories, files = set(), set()

        ret = self.local.listdir(path)
        directories.update(ret[0])
        files.update(ret[1])

        try:
            ret = self.remote.listdir(path)
        except Exception:
            pass
        else:
            directories.update(ret[0])
            files.update(ret[1])

        return (list(directories), list(files))

    def size(self, name):
        return self._get_storage(name).size(name)

    def url(self, name):
        return self._get_storage(name).url(name)

    def accessed_time(self, name):
        return self._get_storage(name).accessed_time(name)

    def created_time(self, name):
        return self._get_storage(name).created_time(name)

    def modified_time(self, name):
        return self._get_storage(name).modified_time(name)


class LocalFileSystemStorage(FileSystemStorage):
    STORAGE_ROOT_NAME = 'LOCAL_MEDIA_ROOT'


class QueuedFileSystemStorage(QueuedStorage):
    LOCAL_STORAGE = LocalFileSystemStorage()
    REMOTE_STORAGE = FileSystemStorage()
