#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vnet_driver.py
 Author: longhui
 Created Time: 2018-03-05 14:11:03
'''

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class VnetDriver(object):
    '''
    base class of
    '''

    def __init__(self, hostname=None, user="root", passwd=""):
        self.hostname = hostname
        self.user = user
        self.passwd = passwd

