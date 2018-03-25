#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: signal_utils.py
 Author: longhui
 Created Time: 2018-03-24 22:18:06
"""

import signal


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

