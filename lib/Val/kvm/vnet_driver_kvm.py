#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vnet_driver_kvm.py
 Author: longhui
 Created Time: 2018-03-14 13:01:13
'''

import libvirt
from lib.Val.vnet_driver import VnetDriver
from lib.Log.log import log

DEFAULT_HV = "qemu:///session"


class QemuVnetDriver(VnetDriver):

    def __init__(self, hostname=None, user=None, passwd=None):
        VnetDriver.__init__(self, hostname, user, passwd)
        self._hypervisor_handler = None

        self._auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], self._request_cred, None]
        # conn = libvirt.open(name) need root username
        # conn = libvirt.openReadOnly(name) has not write promission
        # self._hypervisor_root_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system'), self._auth, 0)

        self._hypervisor_root_handler = None

        log.debug("Try to connect to libvirt in host: %s", self.hostname)
        if self.hostname is None:
            self._hypervisor_handler = libvirt.open(DEFAULT_HV)
        else:
            self._hypervisor_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system'), self._auth, 0)

    def _request_cred(self, credentials, user_data):
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = self.user
            elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                credential[4] = self.passwd
        return 0

    def __del__(self):

        if self._hypervisor_handler:
            log.debug("try to close the connect to libvirt: %s", self.hostname)
            self._hypervisor_handler.close()

    def get_handler(self):
        '''
        return the handler of the virt_driver
        '''
        if self._hypervisor_handler:
            return self._hypervisor_handler

        if self.hostname is None:
            self._hypervisor_handler = libvirt.open(DEFAULT_HV)
        else:
            self._hypervisor_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system'), self._auth, 0)

        if not self._hypervisor_handler:
            return None

        return self._hypervisor_handler

    def delete_handler(self):
        """
         close the connect to host
        :return:
        """
        if self._hypervisor_handler:
            self._hypervisor_handler.close()
        self._hypervisor_handler = None

    def get_network_list(self):
        """
        @return: return all the switch/bridge names on host
        """
        raise NotImplementedError()

    def is_network_exist(self, network_name):
        """
        @param network_name: the name of network created on bridge(when use linux bridge) or switch(when use openvswitch)
        @return: Ture if exist or False
        """

    def get_all_devices(self):
        """
        @return: return list of all the interfaces device names in host
        """
        raise NotImplementedError()

    def get_device_infor(self, device_name=None):
        """
        @param device_name: name of interface in host
        @return: return a dict with key: DNS,IP,MTU,MAC,netmask,gateway,network, etc.
        """
        raise NotImplementedError()

    def get_all_vifs_indexes(self, inst_name):
        """
        @param inst_name: vm name
        @return: a list of all the index of interface device in guest VM
        """
        raise NotImplementedError()

    def is_vif_exist(self, inst_name, vif_index):
        """
        @param vif_index: the interface index in guest VM
        @return: True if exist else False
        """
        raise NotImplementedError()

    def create_new_vif(self, inst_name, vif_index, device_name=None, network=None, MAC=None):
        """
        @param inst_name: name of the guest VM
        @param device_name: device name on the host which the network belong to
        @param vif_index: index of interface in guest VM
        @return: a virtual interface object in guest VM
        """
        raise NotImplementedError()

    def destroy_vif(self, inst_name, vif_index):
        """
        @param vif_ref: reference object to virtual interface in guest VM
        """
        raise NotImplementedError()

    def plug_vif_to_vm(self, inst_name, vif_index):
        """
        @description: Hotplug the specified VIF to the running VM
        @param vif_index: virtual interface index
        @return: Ture if success else False
        """
        raise NotImplementedError()

    def unplug_vif_from_vm(self, inst_name, vif_index):
        """
        @description Hot-unplug the specified VIF from the running VM
        @param vif_index: virtual interface index
        @return: Ture if success else False
        """
        raise NotImplementedError()
