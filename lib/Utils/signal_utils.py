#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: signal_utils.py
 Author: longhui
 Created Time: 2018-03-24 22:18:06
"""

import signal
import functools
from lib.Log.log import log


class TimeoutError(Exception):
    pass


def timeout_handler(signal_num, frame):
    """
    :param signal_num:
    :param frame:
    :return:
    """
    raise TimeoutError("Timeout signal raised.")


def timeout_func(func, timeout_duration=1, default_ret=None, *args, **kwargs):
    """
    :param func:
    :param timeout_duration:
    :param default_ret:
    :param args:
    :param kwargs:
    :return:
    """

    # set the timeout handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_duration)
    try:
        result = func(*args, **kwargs)
    except TimeoutError as exc:
        result = default_ret
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

    return result


def timeout_decrator(time_wait=3, default_ret=None):
    def decrator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(time_wait)
            try:
                return func(*args, **kwargs)
            except TimeoutError as error:
                log.warn(error)
                return default_ret
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        return wrapper
    return decrator


@timeout_decrator()
def test_wrapper(timeout=1):
    print("In test wrapper..")
    print("name:%s" % test_wrapper.__name__)
    import time
    time.sleep(timeout)
    return True


if __name__ == "__main__":
    for time in [1, 2, 3, 4]:
        res = test_wrapper(time)
        print "time=%s, value=%s"  % (time, res)
