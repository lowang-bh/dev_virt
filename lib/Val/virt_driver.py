#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Pw @ 2018-02-07 11:15:48

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class VirtDriver(object):
    '''
    abstract class for virt driver
    '''

    def __init__(self, hostname=None, user=None, passwd=None):
        self.hostname = hostname
        self.user = user
        self.passwd = passwd

    @abc.abstractmethod
    def is_instance_exists(self, inst_name):
        '''
        :description check whether the instance exists in virt-platform
        :param inst_name: the instance name
        :return True or False,
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def create_instance(self, inst_name, reference_vm):
        '''
        @param inst_name: new instance name
        @param reference_vm: template name
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def is_instance_running(self, inst_name):
        '''
        @param inst_name: instance name
        '''
        raise NotImplementedError()

