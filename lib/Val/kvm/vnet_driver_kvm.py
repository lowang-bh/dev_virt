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
        except libvirtError as e:
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

        for interface_dom in self._hypervisor_handler.listAllInterfaces():
            interface_tree = xmlEtree.fromstring(interface_dom.XMLDesc())
            if interface_tree.attrib.get('type') == 'bridge':
                bridge_name = interface_tree.get('name')
                if bridge_name not in bridge_name_list:
                    bridge_name_list.append(bridge_name)

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
        @param network_name:the name of network created on bridge(when use linux bridge) or switch(when use openvswitch)
        @return: True if exist or False
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
        ip_element = device_tree.find("protocol[@family='ipv4']/ip")
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

    # VM interface API
    def set_mac_address(self, inst_name, eth_index, new_mac):
        """
        <mac address='52:54:00:68:43:c2'/>
        """
        domain = self._get_domain_handler(domain_name=inst_name)
        if not domain:
            log.error("Domain %s doesn't exist, set mac failed.", inst_name)
            return False

        if domain.isActive():
            log.warn("New MAC will take effect after domain reboot.")

        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            interface = vif_list[eth_index]
            mac_element = interface.find("mac")
            old_mac = mac_element.get("address")
        except IndexError:
            log.exception("No interfaces at index [%s] find in domain [%s]",eth_index, inst_name)
            return False

        tree = xmlEtree.fromstring(domain.XMLDesc())
        mac_list = tree.findall('devices/interface/mac')
        try:
            for mac_element in mac_list:
                if mac_element.get("address") == old_mac:
                    log.debug("Change old mac [%s] to new [%s] on interface index %s", old_mac, new_mac, eth_index)
                    mac_element.set("address", new_mac)
        except ValueError as error:
            log.exception("Exception when set mac: %s on domain: [%s]", error, inst_name)
            return False

        domain_xml = xmlEtree.tostring(tree)

        # after change the xml, redeine it
        hv_handler = self.get_handler()
        if not hv_handler:
            log.error("Can not connect to host: %s when create domain %s.", self.hostname, inst_name)
            return False
        try:
            # if failed it will raise libvirtError, return value is always a Domain object
            _ = hv_handler.defineXML(domain_xml)
        except libvirtError:
            log.error("Create domain %s failed when define by xml after set MAC.", inst_name)
            return False

        return True

    def get_mac_address(self, inst_name, eth_index):
        """
        :param eth_index: index of virtual interface
        :return:
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)

        # tree = xmlEtree.fromstring(domain.XMLDesc())
        # mac_list = tree.findall('devices/interface/mac')
        try:
            interface = vif_list[eth_index]
            mac_element = interface.find("mac")
            return mac_element.get("address")
        except IndexError:
            log.error("No interfaces at index [%s] find in domain [%s]",eth_index, inst_name)
            return None

    def _get_dom_interfaces_elements_list(self, inst_name):
        """
        :param inst_name:
        :return: a list of interface element, sorted with the slot of interfaces
        """
        if not self._hypervisor_handler:
            self._hypervisor_handler = self.get_handler()

        domain = self._get_domain_handler(domain_name=inst_name)
        if not domain:
            log.error("Domain %s doesn't exist, can not get interfaces information.", inst_name)
            return []

        interface_dict = {}
        tree = xmlEtree.fromstring(domain.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))
        interface_list = tree.findall('devices/interface')
        for interface in interface_list:
            address_element = interface.find('address')
            slot = address_element.attrib.get('slot', None)
            if slot:
                interface_dict[int(slot, 16)] = interface
        # a list of interface element, sorted by interface/address/slot.
        return [interface_dict[key] for key in sorted(interface_dict)]

    def get_all_vifs_indexes(self, inst_name):
        """
        @param inst_name: vm name
        @return: a list of all the index of interface device
        """
        return [i for i in range(len(self._get_dom_interfaces_elements_list(inst_name)))]

    def is_vif_exist(self, inst_name, vif_index):
        """
        @param vif_index: the interface index in guest VM, a integer number
        @return: True if exist else False
        """
        if int(vif_index) in self.get_all_vifs_indexes(inst_name):
            return True
        else:
            return False

    def create_new_vif(self, inst_name, vif_index=None, device_name=None, network=None, bridge=None, MAC=None):
        """
        @param inst_name: name of the guest VM
        @param vif_index: does not need it
        @param device_name: device name on the host which the network belong to
        @:param network: network name defined by libvirt
        @:param bridge: bridge name, may be linux bridge or openvswitch bridge
        @return: a virtual interface xmlElement in guest VM
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)

        if bridge is not None:
            vif_element = self._create_vif_with_bridge(bridge, MAC)
        elif network is not None:
            vif_element = self._create_vif_with_network(network, MAC)
        elif device_name is not None:
            vif_element = self._create_vif_with_device(device_name, MAC)
        else:
            log.error("No network or bridge supply to create a vif.")
            return None
        if vif_element is None:
            return None

        dom = self._get_domain_handler(domain_name=inst_name)
        try:
            dom.attachDeviceFlags(xmlEtree.tostring(vif_element), libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        except libvirtError as error:
            log.error("Exceptions when create a new vif: %s", error)
            return None

        return vif_element

    def _create_vif_with_device(self, device_name, MAC=None):
        """
        """
        bridge_name = self.get_bridge_name(device_name)
        if  bridge_name == "unKnown":
            log.error("Can not find a bridge with physical interface:%s", device_name)
            return None

        vif_xml = """
            <interface type='bridge'>
                <source bridge='%s'/>
                <model type='virtio'/>
            </interface>""" % (bridge_name)
        vif_element = xmlEtree.fromstring(vif_xml)
        if MAC:
            mac_elment = xmlEtree.SubElement(vif_element, "mac")
            mac_elment.attrib['address'] = str(MAC)

        return vif_element

    def _create_vif_with_bridge(self, bridge_name, MAC=None):
        """
        :param bridge_name:
        :param MAC:
        :return: a interface element
        """
        vif_xml = """
          <interface type='bridge'>
            <source bridge='%s'/>
            <model type='virtio'/>
          </interface>""" % (bridge_name)
        vif_element = xmlEtree.fromstring(vif_xml)
        if MAC:
            mac_elment = xmlEtree.SubElement(vif_element, "mac")
            mac_elment.attrib['address'] = str(MAC)

        return vif_element

    def _create_vif_with_network(self, network_name, MAC=None):
        """
        :param bridge_name:
        :param MAC:
        :return: a interface element
        """
        vif_xml = """
          <interface type='network'>
            <source network='%s'/>
            <model type='virtio'/>
          </interface>""" % (network_name)
        vif_element = xmlEtree.fromstring(vif_xml)
        if MAC:
            mac_elment = xmlEtree.SubElement(vif_element, "mac")
            mac_elment.attrib['address'] = str(MAC)

        return vif_element

    def destroy_vif(self, inst_name, vif_index):
        """
        In order to be keep same with Xen, destroy it in config
        @param vif_index: reference object to virtual interface in guest VM
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            vif = vif_list[int(vif_index)]
        except (IndexError, ValueError):
            log.error("No vif with index %s found in domain %s", vif_index, inst_name)
            return False

        dom = self._get_domain_handler(domain_name=inst_name)
        try:
            if dom.isActive():
                ret = dom.detachDeviceFlags(xmlEtree.tostring(vif), libvirt.VIR_DOMAIN_AFFECT_CONFIG)
            else:
                ret = dom.detachDeviceFlags(xmlEtree.tostring(vif))
        except libvirtError as error:
            log.error("Exceptions when destroy vif: %s", error)
            return False

        return ret == 0

    def plug_vif_to_vm(self, inst_name, vif_index):
        """
        @description: Hotplug the specified VIF to the running VM
        @param vif_index: virtual interface index
        @return: True if success else False
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            vif = vif_list[int(vif_index)]
        except (IndexError, ValueError):
            log.error("No vif with index %s found in domain %s", vif_index, inst_name)
            return False

        dom = self._get_domain_handler(domain_name=inst_name)
        try:
            if dom.isActive():
                ret = dom.attachDeviceFlags(xmlEtree.tostring(vif), libvirt.VIR_DOMAIN_AFFECT_LIVE)
                return ret == 0
            else:
                # ret = dom.attachDeviceFlags(xmlEtree.tostring(vif))
                return True
        except libvirtError as error:
            log.error("Exceptions when plug vif: %s", error)
            return False

    def unplug_vif_from_vm(self, inst_name, vif_index):
        """
        @description Hot-unplug the specified VIF from the running VM
        @param vif_index: virtual interface index
        @return: True if success else False
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            vif = vif_list[int(vif_index)]
        except (IndexError, ValueError):
            log.error("No vif with index %s found in domain %s", vif_index, inst_name)
            return False

        dom = self._get_domain_handler(domain_name=inst_name)
        try:
            if dom.isActive():
                ret = dom.detachDeviceFlags(xmlEtree.tostring(vif), libvirt.VIR_DOMAIN_AFFECT_LIVE)
            else:
                # ret = dom.detachDeviceFlags(xmlEtree.tostring(vif))
                return True
        except libvirtError as error:
            log.error("Exceptions when unplug vif: %s", error)
            return False

        return ret == 0

    def __get_mac_and_ip(self, element):
        """
        :param element:
        :return: mac and ip tuple
        """
        try:
            mac = element.find("mac").attrib.get("address", None)
            ip_str = ".".join(["%s" % (int(item, 16)) for item in str(mac).split(":")[2:]])
            return (mac, ip_str)
        except (ValueError, IndexError):
            return (None, None)

    def get_vif_ip(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return:
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name=inst_name)

        for index, element in enumerate(vif_list):
            if index == int(vif_index):
                log.warn("The ip was mapped from MAC, make sure your domain get IP mapped from MAC.")
                _, ip_str = self.__get_mac_and_ip(element)
                return ip_str
        else:
            log.warn("No virtual interface with index [%s] in domain: [%s].", vif_index, inst_name)
            return None

    def get_vif_info(self, inst_name, vif_index):
        """
        return a dict of vif information, MAC, IP, etc
        :param inst_name:
        :param vif_index:
        :return:
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name=inst_name)
        vif_dict = {}

        for index, element in enumerate(vif_list):
            if index == int(vif_index):
                log.warn("The ip was mapped from MAC, make sure your domain get IP mapped from MAC.")
                mac, ip_str = self.__get_mac_and_ip(element)
                vif_dict.setdefault("mac", mac)
                vif_dict.setdefault('ip', ip_str)
                return vif_dict
        else:
            log.warn("No virtual interface with index [%s] in domain: [%s].", vif_index, inst_name)
            return vif_dict

    def get_all_vif_info(self, inst_name):
        """
        :return: return all the VIFs's information: mac and IP
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        vifs_info = {}

        log.warn("The IP was mapped from MAC, make sure your domain get IP mapped from MAC.")
        for index, element in enumerate(vif_list):
            mac, ip_str = self.__get_mac_and_ip(element)
            vifs_info[index] = {'mac': mac, 'ip': ip_str}

        return vifs_info


    def get_vif_network_name(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return: the bridge name which the vif attached to
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            tree = vif_list[int(vif_index)]
        except (IndexError, ValueError) as error:
            log.error("No vif with index: %s", vif_index)
            return None
        source_element = tree.find('source')
        try:
            netwrok_name  = source_element.get('network', None)
            return netwrok_name
        except AttributeError:
            log.error("No interface with index %s on domain: %s", vif_index, inst_name)
            return None

    def get_vif_bridge_name(self, inst_name, vif_index):
        """
        :param inst_name:
        :param vif_index:
        :return: the bridge name which the vif attached to
        """
        vif_list = self._get_dom_interfaces_elements_list(inst_name)
        try:
            tree = vif_list[int(vif_index)]
        except (IndexError, ValueError):
            log.error("No vif with index: %s", vif_index)
            return None

        source_element = tree.find('source')
        try:
            bridge_name  = source_element.get('bridge', None)
            if bridge_name is None:
                network = source_element.get("network", None)
                if network:
                    network_dom =  self._hypervisor_handler.networkLookupByName(network)
                    bridge_name = network_dom.bridgeName()

            return bridge_name
        except AttributeError:
            log.error("No interface with index %s on domain: %s", vif_index, inst_name)
            return None

    # Host network API
    def get_host_manage_interface_infor(self):
        """
        The manage interface, or the default interface configured with a managed IP
        :return:
        """
        try:
            raise NotImplementedError()
        except NotImplementedError:
            log.warn("get host manage interface is not supported in KVM by now.")

        return {}

    def get_host_bond_info(self):
        """
        :return: return the bond information
        """
        try:
            raise NotImplementedError()
        except NotImplementedError:
            log.warn("Get host bond info is not supported in KVM by now.")

        return {}

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


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    (options, args) = parser.parse_args()
    virt = QemuVnetDriver(hostname=options.host, user=options.user, passwd=options.passwd)
    mac = "52:54:c0:a8:7a:c9"
    # vif_element = virt.create_new_vif("test", 2, network="default", MAC=mac)
    # print xmlEtree.tostring(vif_element)

    # print virt.plug_vif_to_vm(inst_name="test", vif_index=2)

    # ----unplug vif and destroy it-----
    # print virt.unplug_vif_from_vm(inst_name="test", vif_index=2)
    # print virt.destroy_vif(inst_name="test", vif_index=2)
    virt.set_mac_address("new_vm", 1, "52:54:c0:a8:01:c9")
    virt.create_new_vif("new_vm", 2, network="default", MAC=mac)
    # virt.set_mac_address("new_vm", 2, mac)
    # pifs = virt.get_all_devices()
    # print pifs
    # for pif in pifs:
    #     print virt.get_bridge_name(pif)
    #
    #
    # print virt._get_dom_interfaces_elements_list(inst_name="test")
    # print virt.get_all_vifs_indexes(inst_name="test")
    # print virt.destroy_vif("test", 2)
