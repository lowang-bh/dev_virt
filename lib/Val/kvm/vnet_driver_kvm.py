#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vnet_driver_kvm.py
 Author: longhui
 Created Time: 2018-03-14 13:01:13
'''

import libvirt
import signal
import xml.etree.ElementTree as xmlEtree
from libvirt import libvirtError
from ipaddress import IPv4Address
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
            log.debug("Can not connect to url: %s, error: %s. Retrying...", url, error)
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

    def _get_domain_handler(self, domain_name=None, domain_id=None):
        """
        get domain handler under qemu, in future, we could have a cache layer
        :param domain_name: the instanse name with the format support by libvirt
        :return:
        """
        hv_handler = self.get_handler()
        if not hv_handler:
            log.error("cannot find the connection to qemu")
            return None

        if domain_id is None and domain_name is None:
            log.error("Both domain ID and Name is None.")
            return None
        try:
            if domain_name:
                dom = hv_handler.lookupByName(domain_name)
            else:
                dom = hv_handler.lookupByID(domain_id)
            return dom
        except libvirtError, e:
            log.exception(str(e))
            return None

    def delete_handler(self):
        """
         close the connect to host
        :return:
        """
        if self._hypervisor_handler:
            self._hypervisor_handler.close()
        self._hypervisor_handler = None

    def get_bridge_list(self):
        """
        @return: return all the switch/bridge names on host
        @note: can not list the bridge which is not defined by xml
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        bridge_name_list = []
        for netdom in self._hypervisor_handler.listAllNetworks():
            bridge_name_list.append(netdom.bridgeName())

        return bridge_name_list

    def get_network_list(self):
        """
        return all the switch/bridge/network on host
        """
        all_network = self._hypervisor_handler.listAllNetworks()
        network_names = [network.name() for network in all_network]
        return network_names

    def is_bridge_exist(self, bridge_name):
        """
        :param bridge_name:
        :return:
        """
        if bridge_name in self.get_bridge_list():
            return True
        else:
            return False

    def is_network_exist(self, network_name):
        """
        @param network_name: the name of network created on bridge(when use linux bridge) or switch(when use openvswitch)
        @return: Ture if exist or False
        """
        if network_name in self.get_network_list():
            return True
        else:
            return False

    def get_all_devices(self):
        """
        @return: return list of all the interfaces device names in host
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()
        try:
            return [pif.name() for pif in self._hypervisor_handler.listAllInterfaces()]
        except libvirt.libvirtError as error:
            log.error("Exceptions raised when get all devices: %s", error)
            return []

    def get_device_infor(self, device_name=None):
        """
        @param device_name: name of interface in host
        @return: return a dict with key: DNS,IP,MTU,MAC,netmask,gateway,network, etc.
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()
        try:
            device_dom = self._hypervisor_handler.interfaceLookupByName(device_name)
        except libvirtError as error:
            log.error("Exception when get device infor: %s", error)
            return {}

        default_infor = {}

        device_tree = xmlEtree.fromstring(device_dom.XMLDesc())
        ip_element =  device_tree.find("protocol[@family='ipv4']/ip")
        if ip_element is not None:
            prefix, ip = ip_element.attrib.get('prefix'), ip_element.attrib.get('address', None)
            default_infor.setdefault('IP', ip)
            default_infor.setdefault('netmask', str(IPv4Address._make_netmask(prefix)[0]))
        else:
            default_infor.setdefault('IP', None)
            default_infor.setdefault('netmask', None)

        default_infor.setdefault('device', device_name)
        default_infor.setdefault('DNS',  None)
        default_infor.setdefault('MAC', device_dom.MACString())
        default_infor.setdefault('gateway',  None)

        return default_infor

    def set_mac_address(self, inst_name, eth_index, mac):
        '''
        <mac address='52:54:00:68:43:c2'/>
        '''
        vm_name = inst_name
        domain = self._get_domain_handler(domain_name=vm_name)
        if not domain:
            log.error("Domain %s doesn't exist, set mac failed.", inst_name)
            return False
        if domain.isActive():
            self.power_off_vm(vm_name)

        tree = xmlEtree.fromstring(domain.XMLDesc())
        mac_list = tree.findall('devices/interface/mac')
        try:
            mac_element = mac_list[eth_index]
            log.debug("Change mac to %s on interface index %s", mac, eth_index)
        except IndexError:
            log.error("No interface with index %s on domain: %s", eth_index, inst_name)
            return False

        mac_element.set('address', mac)
        domain_xml = xmlEtree.tostring(tree)

        # after change the xml, redeine it
        hv_handler = self.get_handler()
        if not hv_handler:
            log.error("Can not connect to host: %s when create domain %s.", self.hostname, vm_name)
            return False
        try:
            # if failed it will raise libvirtError, return value is always a Domain object
            _ = hv_handler.defineXML(domain_xml)
        except libvirtError:
            log.error("Create domain %s failed when define by xml.", vm_name)
            return False

        return True

    def get_mac_address(self, inst_name, eth_index):
        """
        :param eth_index: index of virtual interface
        :return:
        """
        domain = self._get_domain_handler(domain_name=inst_name)
        if not domain:
            log.error("Domain %s doesn't exist, set mac failed.", inst_name)
            return None

        tree = xmlEtree.fromstring(domain.XMLDesc())
        mac_list = tree.findall('devices/interface/mac')
        try:
            mac_element = mac_list[eth_index]
        except IndexError:
            log.error("No interface with index %s on domain: %s", eth_index, inst_name)
            return None

        return mac_element.get('address')  # If no key with address, will return None

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
        This is not always work for KVM, need to improve
        :param device_name:
        :return:
        """
        if not self._hypervisor_handler:
            self._hypervisor_handler = self.get_handler()

        for interface_dom in self._hypervisor_handler.listAllInterfaces():
            if interface_dom.name() == device_name:
                interface_tree = xmlEtree.fromstring(interface_dom.XMLDesc())
                if interface_tree.attrib.get('type') == 'bridge':
                    return interface_tree.attrib.get('name')

        return 'unKnown'


