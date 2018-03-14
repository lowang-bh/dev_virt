#!/usr/bin/env python
#! -*- coding: utf-8 -*-
#########################################################################
# File Name: virt_driver_kvm.py
# Attentions: provide command API for operations on KVM VMs
# Author: longhui
# Created Time: 2018-02-08 11:32:30
#########################################################################

import os
import subprocess
import libvirt
import xml.etree.ElementTree as xmlEtree
from libvirt import libvirtError
from lib.Val.virt_driver import VirtDriver
from lib.Log.log import log

# power state: libvirt.
# VIR_DOMAIN_NOSTATE,
# VIR_DOMAIN_RUNNING,
# VIR_DOMAIN_BLOCKED,
# VIR_DOMAIN_PAUSED,
# VIR_DOMAIN_SHUTDOWN,
# VIR_DOMAIN_SHUTOFF,
# VIR_DOMAIN_CRASHED,
# VIR_DOMAIN_PMSUSPENDED,
# VIR_DOMAIN_LAST, guard

# domain info:
# state
DOMAIN_INFO_STATE = 0
DOMAIN_INFO_MAX_MEM = 1
DOMAIN_INFO_MEM = 2
DOMAIN_INFO_CPUS = 3
DOMAIN_INFO_CPU_TIME = 4

# qemu:///session is for non-root user
DEFAULT_HV = "qemu:///session"

HV_EXE_SUCCESS = 0
HV_EXE_ERROR = -1

# the vm's disk should be in VM_HOUSE
VM_HOUSE = "/datastore/"

# the xml file pool, which contains all the xml templates
TEMPLATE_CFG_POOL = "/etc/libvirt/qemu/"  # default path


class QemuVirtDriver(VirtDriver):
    '''
    derived class of VirtDriver
    '''

    def __init__(self, hostname=None, user=None, passwd=None):
        VirtDriver.__init__(self, hostname, user, passwd)
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

    def _get_root_handler(self):
        """
        Return the root handler of libvirt
        """
        if self._hypervisor_root_handler:
            return self._hypervisor_root_handler

        self._hypervisor_root_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.hostname, '/system'), self._auth, 0)
        if self._hypervisor_root_handler:
            return self._hypervisor_root_handler

        return None

    def _delete_root_handler(self):
        """
        Release root handler
        """
        if self._hypervisor_root_handler:
            self._hypervisor_root_handler.close()
        self._hypervisor_root_handler = None

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

    def _get_domain_handler(self, domain_name=None, domain_id=None):
        """
        get domain handler under qemu, in future, we could have a cache layer
        domain_name has been transfor to the format support by libvirt
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

    def is_instance_exists(self, inst_name):
        '''
        instance
        '''
        all_domains = self.get_vm_list()
        if inst_name in all_domains:
            return True
        return False

    def create_instance(self, vm_name, reference_vm):
        '''
        '''
        log.debug("enter create_instance %s", vm_name)

        # copy the disk first
        target_disk = ''.join((VM_HOUSE, vm_name, ".qcow2"))  # qcow2 is recommand
        reference_disk = ''.join((VM_HOUSE, reference_vm, ".qcow2"))
        cmd = "\cp -f %s %s" % (reference_disk, target_disk)
        log.debug("%s", cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        _, perr = p.communicate()
        if perr:
            log.error("Create domain %s meet an error when copy disk: %s", vm_name, str(perr))
            return False

        # change the xml
        target_xml = TEMPLATE_CFG_POOL + vm_name + ".xml"
        reference_xml = "".join((VM_HOUSE, reference_vm, ".xml"))
        cmd = "cp %s %s && sed -i 's/%s/%s/g' %s" % (reference_xml, target_xml, reference_vm, vm_name, target_xml)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        _, perr = p.communicate()
        if perr:
            log.error("Create domain %s meet an error when change xml:%s", vm_name, str(perr))
            return False

        hv_handler = self.get_handler()
        if not hv_handler:
            log.error("Can not connect to host: %s when create domain %s.", self.hostname, vm_name)
            return False
        if vm_name in [dom.name() for dom in hv_handler.listAllDomains()]:
            log.info("Vm %s is registered.", vm_name)
            return True

        with open(target_xml) as xml_file:
            xml = xml_file.read()
        try:
            # if failed it will raise libvirtError, return value is always a Domain object
            new_dom = hv_handler.defineXML(xml)
        except libvirtError:
            log.error("Create domain %s failed when define by xml.", vm_name)
            return False

        new_dom.setAutostart(1)

        return True

    def create_instance_v1(self, vm_name, image_pool,):
        '''
        use virt-clone will automatically generate the UUID,MAC, this is recommand
        virt-clone -o template_domain -n taget_domain -f disk_path_for_targe_domain
        '''
        reference_vm = image_pool
        log.debug("enter create_instance %s", vm_name)

        target_disk = VM_HOUSE + vm_name + ".qcow2"  # qcow2 is recommand

        cmd = "virt-clone -o %s -n %s -f %s" % (reference_vm, vm_name, target_disk)
        log.debug(cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        pout, perr = p.communicate()
        if "successfully" not in pout:
            log.error("%s,%s", pout, perr)
            return False
        hv_handler = self.get_handler()
        if not hv_handler:
            log.error("Can not connect to host: %s when create domain %s.", self.hostname, vm_name)
            return False
        target_xml = TEMPLATE_CFG_POOL + vm_name + ".xml"

        with open(target_xml) as xmlfile:
            xml = xmlfile.read()
        try:
            #if failed it will raise libvirtError, return value is always a Domain object
            _ = hv_handler.defineXML(xml)
        except libvirtError:
            log.error("Create domain %s failed when define by xml.", vm_name)
            return False

        return True

    def delete_instance(self, inst_name):
        '''
        undefine:If the domain is running, it's converted to transient domain, without stopping it.
        If the domain is inactive, the domain configuration is removed.
        '''
        domain = self._get_domain_handler(inst_name)
        if not domain:
            return True

        if domain.isActive():
            domain.destroy()  # It will shutdown the domain force, if it is already shutdown, libvirtError will raise

        try:
            ret = domain.undefine()
            if ret == 0:
                target_disk = VM_HOUSE + inst_name + ".qcow2"
                cmd = "rm -f %s" % target_disk
                log.debug("remove the disk file for %s: %s", inst_name, cmd)
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                _, perr = p.communicate()
                if perr:
                    log.error("Deleting the disk for vm %s meet an error:%s", inst_name, perr)
                    return False

            return ret == 0
        except Exception, error:
            log.exception(error)
            return False

    def power_off_vm(self, inst_name):
        """
        current we do not consider the power states
        :param inst_name:
        :return:
        """
        domain = self._get_domain_handler(domain_name=inst_name)
        if not domain:
            return False

        try:
            # flags will prevent the forceful termination of the guest, and will instead
            # return an error if the guest doesn't terminate by the end of the timeout
            if domain.isActive():
                ret = domain.destroyFlags(flags=1)
                if ret != 0:
                    ret = domain.destroyFlags(flags=0)
                return ret == 0
            else:
                return True
        except Exception, e:
            log.exception(e)
            return False

    def power_on_vm(self, inst_name):
        '''
        domain.create() will power on it
        '''
        log.debug("power on for %s", inst_name)
        dom = self._get_domain_handler(domain_name=inst_name)
        if not dom:
            return False

        try:
            if dom.isActive():
                return True

            ret = dom.create()

            return ret == 0
        except libvirtError:
            return False

    def get_os_type(self, inst_name):
        '''
        get the os type, return string
        '''
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom:
            return dom.OSType()
        else:
            return None

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

        :param eth_if:
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

    def reboot(self, inst_name):
        '''
        refactor
        '''
        domain = self._get_domain_handler(inst_name)
        if not domain:
            log.error("%s does't exist.", inst_name)
            return False
        try:
            ret = domain.reboot()
            return ret == 0
        except libvirtError:
            return False

    def is_instance_running(self, inst_name):
        '''
        whether the instance is running
        '''
        domain = self._get_domain_handler(inst_name)
        if not domain:
            log.debug("%s does not exist", inst_name)
            return False

        stats = domain.info()
        if stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_RUNNING:
            return True
        return False

    def attach_vif_to_vswitch(self, inst_name, eth_index, vswitch=None, domain=None, update_flag=True):
        """
        Attach the guest interface to a vSwitch

        inst_name: Guest VM name
        eth_index: Network interface number in guest, e.g. eth<eth_index>
        """
        if self.is_instance_running(inst_name):
            raise StandardError('VM %s cannot be configured when running' % inst_name)

        if vswitch is None:
            log.error("vSwitch must be specified")
            return False

        if not isinstance(eth_index, int):
            log.error("Param <eth_index> must be an int type")
            return False

        dom_hdl = self._get_domain_handler(inst_name)
        try:
            dom_xml = dom_hdl.XMLDesc()
        except libvirtError, err:
            log.debug(str(err))
            log.error("Failed to fetch the defined XML for %s", inst_name)
            return False

        dom_tree = xmlEtree.fromstring(dom_xml)
        if_node_list = dom_tree.findall('devices/interface')
        if eth_index >= len(if_node_list):
            log.error("No network interface %d defined in %s", eth_index, inst_name)
            return False

        target_if_node = if_node_list[eth_index]
        src_item = target_if_node.find('source')
        if src_item is not None:
            log.debug("Reset <source> to %s for interface %d in %s", vswitch, eth_index, inst_name)
            src_item.attrib['bridge'] = str(vswitch)
        else:
            log.debug("Create new <source> to %s for interface %d in %s", vswitch, eth_index, inst_name)
            new_src_item = xmlEtree.SubElement(target_if_node, 'source')
            new_src_item.attrib['bridge'] = str(vswitch)

        dom_xml = xmlEtree.tostring(dom_tree)

        hv_hdl = self.get_handler()
        try:
            hv_hdl.defineXML(dom_xml)
        except libvirtError, err:
            log.debug(str(err))
            log.error("Failed to define new XML for %s", inst_name)
            return False

        return True

    def detach_vif_from_vswitch(self, inst_name, port, update_flag=True):
        """
        Detach the guest interface to a vSwitch

        inst_name: Guest VM name
        port: Network interface number in guest, e.g. eth<port>
        """
        if self.is_instance_running(inst_name):
            raise StandardError('VM %s cannot be configured when running' % inst_name)

        if not isinstance(port, int):
            log.error("Param <port> must be an int type")
            return False

        dom_hdl = self._get_domain_handler(inst_name)
        try:
            dom_xml = dom_hdl.XMLDesc()
        except libvirtError, err:
            log.debug(str(err))
            log.error("Failed to fetch the defined XML for %s", inst_name)
            return False

        dom_tree = xmlEtree.fromstring(dom_xml)
        if_node_list = dom_tree.findall('devices/interface')
        if port >= len(if_node_list):
            log.error("No network interface %d defined in %s", port, inst_name)
            return False

        # Removing <source> not work here
        """
        target_if_node = if_node_list[port]
        src_item = target_if_node.find('source')
        if src_item is not None:
            log.debug("Remove <source> element from interface %d on %s", port, inst_name)
            target_if_node.remove(src_item)
        else:
            log.debug("<source> element alreay removed from interface %d on %s", port, inst_name)

        """

        dom_xml = xmlEtree.tostring(dom_tree)

        hv_hdl = self.get_handler()
        try:
            hv_hdl.defineXML(dom_xml)
        except libvirtError, err:
            log.debug(str(err))
            log.error("Failed to define new XML for %s", inst_name)
            return False

        return True

    def get_active_vms(self):
        '''
        The method for listing active domain names:listDomainsID
        '''
        hv_hander = self.get_handler()
        id_list = hv_hander.listDomainsID()
        domans_list = [hv_hander.lookupByID(domain_id) for domain_id in id_list]
        return [dom.name() for dom in domans_list]

    def get_vm_list(self):
        """
        Return the VMs from system
        """
        hv_hander = self.get_handler()
        if hv_hander:
            all_domains = hv_hander.listAllDomains()
            return [dom.name() for dom in all_domains]
        else:
            return []

    def __resolve_ver(self, ver):
        """
        Resolve the version string to major, minor and release number
        """
        ver = int(ver)
        major = ver / 1000000
        minor = (ver % 1000000) / 1000
        rel = ver % 1000000 % 1000
        return major, minor, rel

    def get_host_sw_ver(self, short_name=True):
        """
        Return the HV SW version
        """
        hv_handler = self.get_handler()
        try:
            hv_ver = hv_handler.getVersion()
            lib_ver = hv_handler.getLibVersion()
        except libvirtError, e:
            log.debug(str(e))
            log.warn("Could not get HV version")
            return None

        hv_major, hv_minor, hv_rel = self.__resolve_ver(hv_ver)
        lib_major, lib_minor, lib_rel = self.__resolve_ver(lib_ver)

        if short_name:
            return "%d.%d.%d" % (hv_major, hv_minor, hv_rel)
        else:
            return "QEMU %d.%d.%d libvirt %d.%d.%d" % (hv_major, hv_minor, hv_rel, lib_major, lib_minor, lib_rel)

    def get_host_cpu_info(self):
        """
        Return HV CPU info
        """
        ret_cpu_dict = {}
        hv_handler = self.get_handler()
        try:
            # https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/ch03s04s03.html
            hv_info = hv_handler.getInfo()
        except libvirtError, e:
            log.debug(str(e))
            log.warn("Could not get CPU info")
            return ret_cpu_dict

        ret_cpu_dict['cpu_model'] = str(hv_info[0])
        ret_cpu_dict['cpu_cores'] = hv_info[2]
        # return MHz
        ret_cpu_dict['cpu_speed'] = int(hv_info[3]) * 1000 * 1000
        # number of NUMA nodes X number of sockets per node
        ret_cpu_dict['cpu_sockets'] = int(hv_info[4]) * int(hv_info[5])
        return ret_cpu_dict

    def get_host_storage_info(self):
        """
        Return HV storage info
        """
        # Here only the VM storage directory calculated
        disk_info = os.statvfs(VM_HOUSE)
        ret_storage_dict = {}
        ret_storage_dict['size_total'] = disk_info.f_frsize * disk_info.f_blocks
        ret_storage_dict['size_free'] = disk_info.f_frsize * disk_info.f_bfree
        ret_storage_dict['size_used'] = ret_storage_dict['size_total'] - ret_storage_dict['size_free']
        return ret_storage_dict

    def get_host_mem_info(self):
        """
        Return HV memory info
        """
        ret_mem_dict = {}
        hv_handler = self.get_handler()
        try:
            # https://libvirt.org/docs/libvirt-appdev-guide-python/en-US/html/ch03s04s16.html
            mem_info = hv_handler.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS)
        except libvirtError, e:
            log.debug(str(e))
            log.warn("Could not get memory info")
            return ret_mem_dict

        ret_mem_dict['size_total'] = mem_info['total']
        ret_mem_dict['size_free'] = mem_info['free']
        ret_mem_dict['size_used'] = ret_mem_dict['size_total'] - ret_mem_dict['size_free']
        return ret_mem_dict

    def get_host_plat_info(self):
        """
        Return HV platform info
        This needs root permission to do
        """
        ret_plat_dict = {}
        hv_root_hdl = self._get_root_handler()
        try:
            sys_info_xml = hv_root_hdl.getSysinfo(0)
        except libvirtError, e:
            log.debug(str(e))
            log.warn("Could not get platform/system info")
            return ret_plat_dict
        finally:
            self._delete_root_handler()

        # Return as XML format
        sys_node = xmlEtree.ElementTree(xmlEtree.fromstring(sys_info_xml)).find('system')
        for item in sys_node:
            if item.attrib.get('name') == 'manufacturer':
                ret_plat_dict['vendor_name'] = item.text
            if item.attrib.get('name') == 'product':
                ret_plat_dict['product_name'] = item.text
            if item.attrib.get('name') == 'serial':
                ret_plat_dict['serial_number'] = item.text

        return ret_plat_dict

    def get_templates_list(self):
        """
        :description get all the templates on host
        :return a list of tempaltes names
        """
        raise NotImplementedError()

    def is_instance_halted(self, inst_name):
        '''
        @param inst_name: instance name
        '''
        raise NotImplementedError()

