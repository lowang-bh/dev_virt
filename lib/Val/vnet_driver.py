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
        self._hypervisor_handler = None

    def __nonzero__(self):
        if self._hypervisor_handler is None:
            return False
        return True

    @staticmethod
    def timeout_handler(signal_num, frame):
        """
        :param signal_num:
        :param frame:
        :return:
        """
        raise Exception("Timeout signal raised")

    @abc.abstractmethod
    def get_network_list(self):
        """
        @return: return all the switch/bridge names on host
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def is_network_exist(self, network_name):
        """
        @param network_name: the name of network created on bridge(when use linux bridge) or switch(when use openvswitch)
        @return: True if exist or False
        """

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
    def is_vif_exist(self, inst_name, vif_index):
        """
        @param vif_index: the interface index in guest VM
        @return: True if exist else False
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
        @return: True if success else False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unplug_vif_from_vm(self, inst_name, vif_index):
        """
        @description Hot-unplug the specified VIF from the running VM
        @param vif_index: virtual interface index
        @return: True if success else False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vif_info(self, inst_name, vif_index):
        """
        return a dict of vif information, MAC, IP, etc
        :param inst_name:
        :param vif_index:
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_vif_info(self, inst_name):
        """
        :return: return all the VIFs's information: mac and IP
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vif_ip(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_manage_interface_infor(self):
        """
        The manage interface, or the default interface configured with a managed IP
        :return:
        """
        raise NotImplementedError()


