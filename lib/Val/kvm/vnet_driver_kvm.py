#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vnet_driver_kvm.py
 Author: longhui
 Created Time: 2018-03-14 13:01:13
'''

import libvirt
import signal
from lib.Val.vnet_driver import VnetDriver
from lib.Log.log import log

DEFAULT_HV = "qemu:///session"


class QemuVnetDriver(VnetDriver):

    def __init__(self, hostname=None, user=None, passwd=None):
        VnetDriver.__init__(self, hostname, user, passwd)

        self._auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], self._request_cred, None]
        # conn = libvirt.open(name) need root username
        # conn = libvirt.openReadOnly(name) has not write promission
        # self._hypervisor_root_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system'), self._auth, 0)

        self._hypervisor_root_handler = None

        log.debug("Try to connect to libvirt in host: %s", self.hostname)
        self._hypervisor_handler = self.get_handler()

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
        self._hypervisor_handler = None

    def get_handler(self):
        '''
        return the handler of the virt_driver
        '''
        if self._hypervisor_handler:
            return self._hypervisor_handler

        old = signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(4)   #  connetctions timeout set to 4 secs

        try:
            if self.hostname is None:
                url = DEFAULT_HV
                self._hypervisor_handler = libvirt.open(url)
            else:
                url = "{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system')
                self._hypervisor_handler = libvirt.openAuth(url, self._auth, 0)
        except Exception as error:
            log.warn("Can not connect to url: %s, error: %s. Retrying...", url, error)
            signal.alarm(4)
            try:
                url = "{0}{1}{2}".format('qemu+tls://', self.hostname, '/system')
                self._hypervisor_handler = libvirt.openAuth(url, self._auth, 0)
            except Exception as error:
                log.error("Can not connect to url: %s, error: %s ", url, error)
                return None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

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
        raise NotImplementedError()

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

    def get_vif_info(self, inst_name, vif_index):
        """
        return a dict of vif information, MAC, IP, etc
        :param inst_name:
        :param vif_index:
        :return:
        """
        raise NotImplementedError()

    def get_all_vif_info(self, inst_name):
        """
        :return: return all the VIFs's information: mac and IP
        """
        raise NotImplementedError()

    def get_vif_ip(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return:
        """
        raise NotImplementedError()

    def get_host_manage_interface_infor(self):
        """
        The manage interface, or the default interface configured with a managed IP
        :return:
        """
        raise NotImplementedError()

    def get_host_bond_info(self):
        """
        :return: return the bond information
        """
        raise NotImplementedError()

    def get_vif_network_name(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return: the bridge name which the vif attached to
        """
        raise NotImplementedError()

    def get_bridge_name(self, device_name):
        """
        :param device_name:
        :return:
        """
        raise NotImplementedError()

