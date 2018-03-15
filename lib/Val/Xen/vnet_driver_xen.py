#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vnet_driver_xen.py
 Author: longhui
 Created Time: 2018-03-05 14:06:59
 Descriptions:
 host_metrics    PIF_metrics               VIF_metrics    VM_metrics
      |              |                           |            |
     host <-----    PIF    ----->network<-----  VIF----->    VM
'''

import time
from lib.Log.log import log
from lib.Val.vnet_driver import VnetDriver
from lib.Val.Xen import XenAPI

API_VERSION_1_1 = '1.1'


class XenVnetDriver(VnetDriver):
    '''
    '''

    def __init__(self, hostname=None, user="root", passwd=""):
        VnetDriver.__init__(self, hostname, user, passwd)
        self._hypervisor_handler = None

        self._hypervisor_handler = self.get_handler()

    def __del__(self):
        try:
            if self._hypervisor_handler is not None:
                log.debug("Release handler in vnet driver, ID:%s", id(self._hypervisor_handler))
                self._hypervisor_handler.xenapi.session.logout()
                self._hypervisor_handler = None
        except Exception, error:
            log.debug(error)

    def get_handler(self):
        '''
        return the handler of the virt_driver
        '''
        if self._hypervisor_handler is not None:
            return self._hypervisor_handler

        if self.hostname is None:
            self._hypervisor_handler = XenAPI.xapi_local()  #no __nonzero__, can not use if/not for bool test
        else:
            log.debug("connecting to %s with user:%s,passwd:%s", "http://" + str(self.hostname), self.user, self.passwd)
            self._hypervisor_handler = XenAPI.Session("http://" + str(self.hostname))
        try:
            self._hypervisor_handler.xenapi.login_with_password(self.user, self.passwd, API_VERSION_1_1, 'XenVirtDriver')
        except Exception, error:
            log.exception("Exception raised:%s when get handler.", error)
            return None

        log.debug("Get handler ID in vnet driver: %s", id(self._hypervisor_handler))
        return self._hypervisor_handler

    def delete_handler(self):
        '''
        release the session
        '''
        try:
            if self._hypervisor_handler is not None:
                log.debug("Release handler manually in vnet driver, ID:%s", id(self._hypervisor_handler))
                self._hypervisor_handler.xenapi.session.logout()
                self._hypervisor_handler = None
        except Exception, error:
            log.debug(error)

    def get_network_list(self):
        """
        return all the switch/bridge/network on host
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        switch_names_list = []
        for network_ref in self._hypervisor_handler.xenapi.network.get_all():
            switch_names_list.append(self._hypervisor_handler.xenapi.network.get_bridge(network_ref))

        return switch_names_list

    def is_network_exist(self, network_name):
        """
        @param switch_name: the network name of bridge(when use linux bridge) or switch(when use openvswitch)
        @return: Ture if exist or False
        """
        all_switchs = self.get_network_list()
        if network_name in all_switchs:
            return True
        else:
            return False

    def _get_PIF_by_device(self, device_name):
        """
        @param device_name: interface name in Host, eg, eth0,etc
        @return: a PIF reference object about interface
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        all_pifs = self._hypervisor_handler.xenapi.PIF.get_all()
        for pif in all_pifs:
            if device_name == self._hypervisor_handler.xenapi.PIF.get_device(pif):
                return pif
        log.error("No PIF found corresponding with device name [%s].", device_name)
        return None

    def get_all_devices(self):
        """
        @return: return a list of all the interfaces device name in host
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()
        try:
            all_pifs = self._hypervisor_handler.xenapi.PIF.get_all()
            return [self._hypervisor_handler.xenapi.PIF.get_device(pif) for pif in all_pifs]
        except Exception, error:
            log.exception(error)
            return []

    def get_device_infor(self, device_name=None, pif_ref=None):
        """
        @param pif_ref: reference to a PIF object
        @param device_name: name of interface in host
        @return: return a dict with key: DNS,IP,MTU,MAC,netmask,gateway,network, etc.
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        if device_name is not None:
            pif_ref = self._get_PIF_by_device(device_name)
            if not pif_ref:
                log.error("Can not get device infor with given device name:%s.", device_name)
                return {}
            return self._hypervisor_handler.xenapi.PIF.get_record(pif_ref)
        elif pif_ref is not None:
            return self._hypervisor_handler.xenapi.PIF.get_record(pif_ref)
        else:
            log.error("Please specify a device name to get device infor.")
            return {}

    def _get_network_ref_by_device(self, device_name):
        """
        @param device_name: interface name on host that are attached from XenServer hosts to this network
        @return: a reference to the network
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        pif_ref = self._get_PIF_by_device(device_name)
        if pif_ref is None:
            log.debug("Can not get network ref with device name [%s]", device_name)
            return None

        return self._hypervisor_handler.xenapi.PIF.get_network(pif_ref)

    def _get_network_ref_by_bridge(self, bridge_name):
        """
        @param bridge_name: the bridge name description corresponding to this network on the local XenServer host
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        all_networks = self._hypervisor_handler.xenapi.network.get_all()
        for network in all_networks:
            if self._hypervisor_handler.xenapi.network.get_bridge(network) == bridge_name:
                return network

        log.error("No netwrok found with bridge name [%s].", bridge_name)
        return None

    def _create_new_network(self, bridge_name):
        """
        create a new network
        @return: return the reference object of network
        """
        new_network_record = {'MTU': '1500', 'other_config': {}}
        new_network_record['bridge'] = bridge_name
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            return self._hypervisor_handler.xenapi.network.create(new_network_record)
        except Exception, error:
            log.exception("Exceptions: %s", error)
            return None

    def get_all_vifs_indexes(self, inst_name):
        """
        @return: a list of all the index of interface device in guest VM
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
        except IndexError:
            log.error("No VM with name [%s].", inst_name)
            return []
        all_vifs = self._hypervisor_handler.xenapi.VM.get_VIFs(vm_ref)
        return [self._hypervisor_handler.xenapi.VIF.get_device(vif) for vif in all_vifs]

    def is_vif_exist(self, inst_name, vif_index):
        """
        @param vif_index: the interface index in guest VM
        @return: True if exist else False
        """
        if vif_index in self.get_all_vifs_indexes(inst_name):
            return True
        else:
            return False

    def _get_vif_by_index(self, inst_name, vif_index):
        """
        @param vif_index: the interface index  in guest VM
        @return: a reference object to the virtual interface
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
        except IndexError:
            log.error("No VM with name [%s].", inst_name)
            return None
        all_vifs = self._hypervisor_handler.xenapi.VM.get_VIFs(vm_ref)
        for vif in all_vifs:
            if str(vif_index) == self._hypervisor_handler.xenapi.VIF.get_device(vif):
                return vif
        #No vif match with vif_index
        log.debug("No virtual interface with given index:[%s].", vif_index)
        return None

    def create_new_vif(self, inst_name, vif_index, device_name=None, network=None, MAC=None):
        """
        @param inst_name: name of the guest VM
        @param device_name: device name on the host which the network belong to
        @param vif_index: index of interface in guest VM
        @return: a reference to virtual interface in guest VM
        to change the MTU, please set it in other-config:mtu=9000
        """
        record = {'MAC': '',
                 'MAC_autogenerated': True,
                 'MTU': '0',
                 'other_config': {},
                 'qos_algorithm_params': {},
                 'qos_algorithm_type': ''}

        handler = self.get_handler()
        vm_ref_list = handler.xenapi.VM.get_by_name_label(inst_name)
        if not vm_ref_list:
            log.error("No instance with name [%s].", inst_name)
            return False

        network_ref = None
        if device_name is not None:
            network_ref = self._get_network_ref_by_device(device_name)
        elif network is not None:
            network_ref = self._get_network_ref_by_bridge(bridge_name=network)
        if network_ref is None:
            log.error("No valide network found with params: NIC:%s, bridge:%s.", device_name, network)
            return None

        allows_index = handler.xenapi.VM.get_allowed_VIF_devices(vm_ref_list[0])
        if str(vif_index) not in allows_index:
            log.error("Virtual interface device [%s] is not allowed, allowed:%s", vif_index, allows_index)
            return None

        record['VM'] = vm_ref_list[0]
        record['network'] = network_ref
        record['device'] = str(vif_index)
        if MAC is not None:  #if MAC given, MAC_autogenerated will be False
            record['MAC'] = MAC
        log.debug("create new vif with record:%s", str(record))
        new_vif = handler.xenapi.VIF.create(record)
        return new_vif

    def destroy_vif(self, inst_name, vif_index):
        """
        @param vif_index: index of virtual interface in guest VM
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        vif_ref = self._get_vif_by_index(inst_name, vif_index)
        if vif_ref is None:
            log.error("No virtual interface device found with index [%s] when try to destroy vif.", vif_index)
            return False

        # unplug in allowed_operations, means the vif has plugged in VM
        if 'unplug' in self._hypervisor_handler.xenapi.VIF.get_record(vif_ref)['allowed_operations']:
            log.error("Error when destroy, please firstly unplug the VIF or power off the VM.")
            return False

        try:
            self._hypervisor_handler.xenapi.VIF.destroy(vif_ref)
        except Exception, error:
            log.exception("Exceptions raised when destroy VIF:%s", error)
            return False
        return True

    def plug_vif_to_vm(self, inst_name, vif_index):
        """
        Hotplug the specified VIF, dynamically attaching it to the running VM
        @param vif_index: virtual interface index
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        vif_ref = self._get_vif_by_index(inst_name, vif_index)
        if vif_ref is None:
            log.error("No vif found with index [%s] when try to attach vif.", vif_index)
            return False

        vm_ref = self._hypervisor_handler.xenapi.VIF.get_VM(vif_ref)
        power_status = self._hypervisor_handler.xenapi.VM.get_record(vm_ref)['power_state']
        allowed_opera = self._hypervisor_handler.xenapi.VIF.get_record(vif_ref)['allowed_operations']
        if 'plug' not in allowed_opera and power_status == 'Running':
            log.info("VIF [%s] is already pluged.", vif_index)
            return True

        try:
            self._hypervisor_handler.xenapi.VIF.plug(vif_ref)
        except Exception, error:
            log.error("Exception raised when hot-plug a VIF:%s.", error)
            return False
        return True

    def unplug_vif_from_vm(self, inst_name, vif_index):
        """
        Hot-unplug the specified VIF, dynamically unattaching it from the running VM
        @param vif_index: virtual interface index
        @note It should check the power_state before use this API
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        vif_ref = self._get_vif_by_index(inst_name, vif_index)
        if vif_ref is None:
            log.error("No vif found with index [%s] when try to detach vif.", vif_index)
            return False

        vm_ref = self._hypervisor_handler.xenapi.VIF.get_VM(vif_ref)
        power_status = self._hypervisor_handler.xenapi.VM.get_record(vm_ref)['power_state']
        allowed_opera = self._hypervisor_handler.xenapi.VIF.get_record(vif_ref)['allowed_operations']
        if 'unplug' not in allowed_opera and power_status == 'Running':
            log.info("VIF [%s] is already unpluged.", vif_index)
            return True

        try:
            self._hypervisor_handler.xenapi.VIF.unplug(vif_ref)
        except Exception, error:
            log.exception("Exceptions raised when unplug a VIF:%s", error)
            return False
        return True

