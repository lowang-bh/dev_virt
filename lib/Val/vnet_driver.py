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

    @abc.abstractmethod
    def get_vswitch_list(self):
        """
        @return: return all the switch/bridge names on host
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_devices(self):
        """
        @return: return list of all the interfaces device names in host
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_device_infor(self, device_name=None):
        """
        @param device_name: name of interface in host
        @return: return a dict with key: DNS,IP,MTU,MAC,netmask,gateway,network, etc.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_vifs_indexes(self, inst_name):
        """
        @param inst_name: vm name
        @return: a list of all the index of interface device in guest VM
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vif_by_index(self, inst_name, vif_index):
        """
        @param vif_index: the interface index in guest VM
        @return: the virtual interface object in VM
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def create_new_vif(self, inst_name, vif_index, device_name=None, network=None, MAC=None):
        """
        @param inst_name: name of the guest VM
        @param device_name: device name on the host which the network belong to
        @param vif_index: index of interface in guest VM
        @return: a virtual interface object in guest VM
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def destroy_vif(self, inst_name, vif_index):
        """
        @param vif_ref: reference object to virtual interface in guest VM
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def plug_vif_to_vm(self, inst_name, vif_index):
        """
        @description: Hotplug the specified VIF to the running VM
        @param vif_index: virtual interface index
        @return: Ture if success else False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unplug_vif_from_vm(self, inst_name, vif_index):
        """
        @description Hot-unplug the specified VIF from the running VM
        @param vif_index: virtual interface index
        @return: Ture if success else False
        """
        raise NotImplementedError()
