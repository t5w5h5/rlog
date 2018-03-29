# rlog: Tag-based logging library for Python 3.
# Copyright: (c) 2018, t5w5h5@gmail.com. All rights reserved.
# License: MIT, see LICENSE for details.

import contextlib
import io
import logging
import unittest
import re
import sys

from rlog import log


@contextlib.contextmanager
def captured_output():
    new_out = io.StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield sys.stdout
    finally:
        sys.stdout = old_out


class TestLog(unittest.TestCase):

    def setUp(self):
        log._log_output_json = False
        log._log_ftime = '-'    # "Disable" output of timestamp.
        log._log_include = []
        log._log_exclude = []

    def test_basics(self):
        with captured_output() as out:
            log.warn([], 'arg1', 'arg2')
            log.simple('arg1', 'arg2')
            log.keywords(kw1='text', kw2=2)
        self.assertEqual(
            out.getvalue(),
            "- ['warn', 'test_log'] arg1 arg2\n"
            "- ['simple', 'test_log'] arg1 arg2\n"
            "- ['keywords', 'test_log'] kw1=text kw2=2\n")

    def test_exceptions(self):
        with captured_output() as out:
            log.debug('no error')
            try:
                open('___unknown_file.___')
            except IOError:
                log.error('Oops')
            try:
                1/0
            except ZeroDivisionError:
                log.error()
        self.assertEqual(
            re.sub('File [^,]*, line [^,]*,', '', out.getvalue(), flags=re.MULTILINE),
            "- ['debug', 'test_log'] no error\n"
            "- ['error', 'test_log'] Oops \n"
            " Traceback (most recent call last):\n"
            "    in test_exceptions\n"
            "    open('___unknown_file.___')\n"
            " FileNotFoundError: [Errno 2] No such file or directory: '___unknown_file.___'\n"
            "\n"
            "- ['error', 'test_log'] Traceback (most recent call last):\n"
            "    in test_exceptions\n"
            "    1/0\n"
            " ZeroDivisionError: division by zero\n"
            "\n")

    def test_redirect(self):
        with captured_output() as out:
            logging.debug('This is the root logger.')
            logger = logging.getLogger('named')
            logger.error('This is a named logger with the two variables %s and %d.', 'a', 1)
            try:
                1/0
            except ZeroDivisionError:
                logging.exception('Oops')
        self.assertEqual(
            re.sub('File [^,]*, line [^,]*,', '', out.getvalue(), flags=re.MULTILINE),
            "- ['debug', 'test_log', 'root'] This is the root logger.\n"
            "- ['error', 'test_log', 'named'] This is a named logger with the two variables a and 1.\n"
            "- ['error', 'test_log', 'root'] Oops \n"
            " Traceback (most recent call last):\n"
            "    in test_redirect\n"
            "    1/0\n"
            " ZeroDivisionError: division by zero\n"
            "\n")

    def test_json(self):
        log._log_output_json = True
        with captured_output() as out:
            log.json(['tag1'], 'Something', 1, kw1='text', kw2=2)
            try:
                1 / 0
            except ZeroDivisionError:
                log.json(['exception'])
        self.assertEqual(
            re.sub('("time": [\d.]*)|(File [^,]*, line [^,]*,)', '', out.getvalue(), flags=re.MULTILINE),
            '{, "tags": ["json", "test_log", "tag1"], "args": ["Something", 1], "kwargs": {"kw1": "text", "kw2": 2}}\n'
            '{, "tags": ["json", "test_log", "exception"], "args": [], "kwargs": {}, "exception": ["ZeroDivisionError", "division by zero", ["Traceback (most recent call last):", "   in test_json\\n    1 / 0", "ZeroDivisionError: division by zero"]]}\n')

    def test_filter(self):
        log._log_include = ['included1', 'included2']
        with captured_output() as out:
            log.print(['included2'], 'This is included.')
            log.print(['excluded2'], 'This is not included.')
            l = logging.getLogger('included1')
            l.error('This is an included standard logger.')
        self.assertEqual(
            out.getvalue(),
            "- ['print', 'test_log', 'included2'] This is included.\n"
            "- ['error', 'test_log', 'included1'] This is an included standard logger.\n")

        log._log_include = []
        log._log_exclude = ['excluded1', 'excluded2']
        with captured_output() as out:
            log.print(['included2'], 'This is not excluded.')
            log.print(['excluded2'], 'This is excluded.')
            l = logging.getLogger('excluded1')
            l.error('This is an excluded standard logger.')
        self.assertEqual(
            out.getvalue(),
            "- ['print', 'test_log', 'included2'] This is not excluded.\n")

        log._log_include = ['included1']
        log._log_exclude = ['excluded1']
        with captured_output() as out:
            log.print(['included2'], 'This is not included.')
            log.print(['included1'], 'This is included and not excluded.')
            log.print(['included1', 'excluded1'], 'This is included and also excluded.')
        self.assertEqual(
            out.getvalue(),
            "- ['print', 'test_log', 'included1'] This is included and not excluded.\n")
