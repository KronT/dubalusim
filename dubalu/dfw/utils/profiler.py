# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import unicode_literals, print_function

import re
import sys
import time
import StringIO
import warnings
from functools import wraps

try:
    import pyinstrument
    from pyinstrument.profiler import NotMainThreadError
except ImportError:
    pyinstrument = None

from format_time import format_time

from django.core.management.color import color_style, no_style


not_main_thread_message = (
    "Signals mode in pyinstrument can only be used on the main thread.\n"
    "For better profiling performance, run your server process in single-threaded mode.\n\n"
    "With the built-in server, you can do this with\n"
    "./manage.py runserver --nothreading --noreload")


class Profiler(object):
    profiler = None
    cprofile = None

    def __init__(self, name="", subcalls=True, builtins=False, sortby='cumulative', print_stats=True, print_callers=False, print_callees=False, file=sys.stdout, cprofile=False, request=None):
        """
        :param sortby: can be ``cumulative``, ``time``, etc.

        """
        try:
            if cprofile or not pyinstrument:
                raise ImportError
            self.profiler = pyinstrument.Profiler()

        except ImportError:
            import cProfile
            self.cprofile = cProfile.Profile(subcalls=subcalls, builtins=builtins)

        self.name = name
        self.sortby = sortby
        self.print_stats = print_stats
        self.print_callers = print_callers
        self.print_callees = print_callees
        self.file = file
        self.request = request if request and hasattr(request, 'profiler') else None

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.finish()

    def start(self):
        if self.profiler:
            try:
                self.profiler.start()
            except NotMainThreadError:
                warnings.warn(not_main_thread_message)
                self.profiler = pyinstrument.Profiler(use_signal=False)
                self.profiler.start()

        elif self.cprofile:
            self.cprofile.enable()

    def finish(self):
        if self.profiler:
            self.profiler.stop()
            if self.request:
                self.request.profiler.append(self.profiler.output_html(template='<style>{css}</style>{body}<script>{js}</script>'))
            if not self.request or self.file is not sys.stdout:
                print(self.profiler.output_text(unicode=True, color=True), file=self.file)

        elif self.cprofile:
            import pstats
            self.cprofile.disable()
            stream = StringIO.StringIO()
            print("##### Profiler %s:" % self.name, file=stream)
            stats = pstats.Stats(self.cprofile, stream=stream)
            if self.sortby:
                stats.sort_stats(self.sortby)
            print("", file=stream)
            if self.print_stats:
                print("=" * 100, file=stream)
                print("Stats:", file=stream)
                stats.print_stats()
            if self.print_callers:
                print("=" * 100, file=stream)
                print("Callers:", file=stream)
                stats.print_callers()
            if self.print_callees:
                print("=" * 100, file=stream)
                print("Callees:", file=stream)
                stats.print_callees()
            text = stream.getvalue()
            text = re.sub(r'(\w:\d+)\(', '\\1 (', text)
            if self.request:
                self.request.profiler.append('<pre>%s</pre>' % text)
            if not self.request or self.file is not sys.stdout:
                print(text, file=self.file)

    def __call__(self, func):
        def wrapped(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        if hasattr(func, 'name'):
            wrapped = wraps(func)(wrapped)
        return wrapped


class Timer(object):
    def __init__(self, fmt=None, file=sys.stdout, end='\n', color=True, **context):
        context['name'] = context.get('name', "Timer")
        self.fmt = fmt or "{name} => elapsed_time: {elapsed_time}, num_calls: {num_calls}, acc_time: {acc_time}"
        self.context = context
        self.start()
        self.acc_time = 0
        self.num_calls = 0
        self.file = file
        self.end = end
        self.style = color_style() if color else no_style()

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.finish()

    def start(self):
        self.begin = time.time()

    def _color_for_time(self, time):
        if time > 1:
            return self.style.ERROR
        elif time > 0.4:
            return self.style.NOTICE
        elif time > 0.1:
            return self.style.SQL_KEYWORD
        elif time > 0.05:
            return self.style.SQL_COLTYPE
        else:
            return self.style.SQL_FIELD

    def finish(self):
        now = time.time()
        elapsed_time = now - self.begin
        self.acc_time += elapsed_time
        self.num_calls += 1
        self.begin = now

        self.context.update(
            elapsed_time=self._color_for_time(elapsed_time)(format_time(elapsed_time)),
            num_calls=self.num_calls,
            acc_time=format_time(self.acc_time),
        )
        print(self.fmt.format(**self.context).encode('utf-8'), file=self.file, end=self.end)

    def __call__(self, func):
        def wrapped(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        if hasattr(func, 'name'):
            wrapped = wraps(func)(wrapped)
        return wrapped
