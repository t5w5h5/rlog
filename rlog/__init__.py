# rlog: Tag-based logging library for Python 3.
# Copyright: (c) 2018, t5w5h5@gmail.com. All rights reserved.
# License: MIT, see LICENSE for details.

"""Tag-based logging library for Python 3."""

import collections as _collections
import datetime as _datetime
import json as _json
import logging as _logging
import os as _os
import queue as _queue
import sys as _sys
import threading as _threading
import traceback as _traceback

__all__ = ['log']


class _RedirectHandler(_logging.Handler):
    """Logging handler to redirect the standard library logging to us.
    The level name, logger name, and module are used as log tags."""

    def emit(self, record):
        log._log([record.levelname.lower(), record.module, record.name], record.msg % record.args)


class _Logger(_threading.Thread):
    """Simple replacement for the standard logging library."""

    def __init__(self):
        _threading.Thread.__init__(self, daemon=True, name='log')
        self._queue = _queue.Queue()
        self._running = _threading.Event()

        self._log_ftime = _os.environ.get('LOG_FTIME', '%x %X.%f')
        self._log_output_json = _os.environ.get('LOG_OUTPUT', 'native').lower() == 'json'
        self._log_threaded = _os.environ.get('LOG_THREADED', 'false').lower() in {'yes', 'y', 'on', '1', 'true'}

        include = _os.environ.get('LOG_INCLUDE')
        self._log_include = [] if not include else include.split(';')
        exclude = _os.environ.get('LOG_EXCLUDE')
        self._log_exclude = [] if not exclude else exclude.split(';')

        # Redirect all standard library logging.
        del _logging.root.handlers[:]
        _logging.root.addHandler(_RedirectHandler())
        _logging.root.setLevel(_logging.getLevelName(_os.environ.get('LOG_LOGGING_LEVEL', 'DEBUG').upper()))

    def _log(self, tags, *args, **kwargs):
        """Do the actual logging."""

        # Apply filters.
        if self._log_include:
            if not any(tag in self._log_include for tag in tags): return
        if self._log_exclude:
            if any(tag in self._log_exclude for tag in tags): return

        # Assemble record.
        record = _collections.OrderedDict([
            ('time', _datetime.datetime.now()),
            ('tags', tags),
            ('args', args),
            ('kwargs', kwargs)
        ])
        exc_type, exc_value, exc_traceback = _sys.exc_info()
        if exc_type:
            record['exception'] = exc_type, exc_value, exc_traceback

        if self._log_threaded:
            self._queue.put(record)
            if not self._running.is_set():
                self._running.set()
                self.start()
        else:
            self._print(record)

    def _print(self, record):
        """Do the actual output."""
        try:
            if self._log_output_json:
                record['time'] = record['time'].timestamp()
                if 'exception' in record:
                    exc_type, exc_value, exc_traceback = record['exception']
                    record['exception'] = (exc_type.__name__, str(exc_value), [_.rstrip() for _ in _traceback.format_exception(*record['exception'])])
                print(_json.dumps(record))
            else:
                if self._log_ftime:
                    out = [record['time'].strftime(self._log_ftime)]
                else:
                    out = ['{:<15.4f}'.format(round(record['time'].timestamp(), 4))]
                out.append(record['tags'])
                out.extend(record['args'])
                out.extend(['{}={}'.format(k, v) for k, v in record['kwargs'].items()])
                if 'exception' in record:
                    if record['args'] or record['kwargs']:
                        out.append(_os.linesep)
                    out.extend(_traceback.format_exception(*record['exception']))
                print(*out)
        except:
            _traceback.print_exc()
        _sys.stdout.flush()

    def run(self):
        while True:
            self._print(self._queue.get())

    def __getattr__(self, method_name):
        """Wrapper for arbitrary log method names.
        Method name and calling module name are added to the log tags."""
        def log_wrapper(*args, **kwargs):
            tags = [method_name]
            try:
                # Extract module name from frame. This code is adapted from the logging library.
                frame = 1
                while True:
                    pathname = _os.path.normcase(_sys._getframe(frame).f_code.co_filename)
                    filename = _os.path.basename(pathname)
                    module_name = _os.path.splitext(filename)[0]
                    if module_name and not module_name.startswith('__'):
                        tags.append(module_name)
                        break
                    frame += 1
            except ValueError:
                pass

            if len(args) == 0 or not isinstance(args[0], list):
                self._log(tags, *args, **kwargs)
            else:
                self._log(tags + args[0], *args[1:], **kwargs)
        return log_wrapper


log = _Logger()
