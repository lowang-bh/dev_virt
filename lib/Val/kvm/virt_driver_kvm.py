#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################################
# File Name: virt_driver_kvm.py
# Attentions: provide command API for operations on KVM VMs
# Author: longhui
# Created Time: 2018-02-08 11:32:30
#########################################################################

import os
import subprocess
import signal
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

    def _get_root_handler(self):
        """
        Return the root handler of libvirt
        """
        if self._hypervisor_root_handler:
            return self._hypervisor_root_handler

        if self.hostname is None:
            hostname = "localhost"
        else:
            hostname = self.hostname
        url = "{0}{1}{2}".format('qemu+tcp://', hostname, '/system')
        old = signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(4)   #  connetctions timeout set to 4 secs
        try:
            self._hypervisor_root_handler = libvirt.openAuth(url, self._auth, 0)
        except Exception as error:
            log.debug("Can not connect to %s, error: %s. Retrying...", url, error)
            url = "{0}{1}{2}".format('qemu+tls://', hostname, '/system')
            signal.alarm(4)
            try:
                self._hypervisor_root_handler = libvirt.openAuth(url, self._auth, 0)
            except Exception as error:
                log.error("Can not connect to url:%s, error: %s", url, error)
                return None

        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

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
        except libvirtError as e:
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
        log.info("enter create_instance %s", vm_name)
        if self.is_instance_exists(vm_name):
            log.error("Already exist domain: %s", vm_name)
            return False

        hv_handler = self.get_handler()
        template_dom = self._get_domain_handler(domain_name=reference_vm)
        template_xml =  template_dom.XMLDesc(libvirt.VIR_DOMAIN_XML_SECURE)
        tree = xmlEtree.fromstring(template_xml)
        name = tree.find("name")
        name.text = vm_name
        uuid = tree.find('uuid')
        tree.remove(uuid)

        # remove MAC for interface
        for interface in tree.findall("devices/interface"):
            elm = interface.find("mac")
            interface.remove(elm)

        # clone disk for new domain
        disk_index = 0
        for disk in tree.findall("devices/disk[@device='disk']"):
            source_elm = disk.find('source')
            source_file = source_elm.get('file')
            suffix = str(os.path.basename(source_file)).split(".")[-1]
            if source_file:
                # if disk_index == 0:
                #     target_file = ".".join([vm_name, suffix])
                # else:
                #     target_file = ".".join([vm_name + "-" + str(disk_index), suffix])

                target_file = ".".join([self._get_available_vdisk_name(vm_name), suffix])
                clone_path = os.path.join(os.path.dirname(source_file), target_file)
                source_elm.set('file', clone_path)
                self.clone_disk(source_file, target_file)
                disk_index += 1

        try:
            # if failed it will raise libvirtError, return value is always a Domain object
            new_dom = hv_handler.defineXML(xmlEtree.tostring(tree))
        except libvirtError:
            log.error("Create domain %s failed when define by xml.", vm_name)
            return False

        new_dom.setAutostart(1)

        return True

    def delete_instance(self, inst_name, delete_disk=False):
        '''
        undefine:If the domain is running, it's converted to transient domain, without stopping it.
        If the domain is inactive, the domain configuration is removed.
        '''
        domain = self._get_domain_handler(inst_name)
        if not domain:
            return True

        if domain.isActive():
            log.info("Try to power off vm [%s] gracefully.", inst_name)
            ret =  domain.destroyFlags(flags=libvirt.VIR_DOMAIN_DESTROY_GRACEFUL)
            if ret != 0:
                log.info("Power off failed, try to poweroff forcely.")
                domain.destroy()  # It will shutdown the domain force, if it is already shutdown, libvirtError will raise

        self.detach_disk_from_domain(inst_name, force=delete_disk)

        try:
            ret = domain.undefine() # may use undefineFlags to handler managed save image or snapshots
        except libvirtError as error:
            log.exception("Exception raise when delete domain [%s]: %s.", inst_name, error)
            return False

        return ret == 0

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
                ret = domain.destroyFlags(flags=libvirt.VIR_DOMAIN_DESTROY_GRACEFUL) # VIR_DOMAIN_DESTROY_GRACEFUL = 1
                if ret != 0:
                    ret = domain.destroyFlags(flags=libvirt.VIR_DOMAIN_DESTROY_DEFAULT)
                return ret == 0
            else:
                return True
        except Exception as e:
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

    def get_os_type(self, inst_name, short_name=True):
        '''
        get the os type, return string
        '''
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom:
            return dom.OSType()  # In KVM it will return hvm
        else:
            return None

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

    # host information API
    def __is_kvm_available(self, xmlfile):
        """
        :param xmlfile:
        :return: return True is kvm is supported, else False
        """
        etree = xmlEtree.fromstring(xmlfile)
        if etree.find("guest/arch/domain/[@type='kvm']") is not None:
            log.debug("host capabilities: type=kvm found, host support KVM")
            return True
        else:
            return False

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
        except libvirtError as e:
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
        except libvirtError as e:
            log.debug(str(e))
            log.warn("Could not get CPU info")
            return ret_cpu_dict

        ret_cpu_dict['cpu_model'] = str(hv_info[0])
        ret_cpu_dict['cpu_cores'] = hv_info[2]
        # return MHz
        ret_cpu_dict['cpu_speed'] = int(hv_info[3])
        # number of NUMA nodes * number of sockets per node
        ret_cpu_dict['cpu_sockets'] = int(hv_info[4]) * int(hv_info[5])
        ret_cpu_dict['cores_per_socket'] = int(hv_info[6])
        #number of threads per core
        ret_cpu_dict['thread_per_core'] = int(hv_info[7])

        return ret_cpu_dict

    def get_host_all_storages(self):
        """
        return a list of all the storage names
        """
        hv_driver = self.get_handler()
        pool_list = hv_driver.listAllStoragePools(0)
        return [pool_dom.name() for pool_dom in pool_list]

    def get_host_storage_info(self, storage_name="default"):
        """
        Return HV storage info: Unit is GB
        """
        # Here only the VM storage directory calculated
        ret_storage_dict = {}
        hv_driver = self.get_handler()
        try:
            pool_dom = hv_driver.storagePoolLookupByName(storage_name)
            # pool.info is a list [Pool state, Capacity, Allocation, Available]
            pool_info = pool_dom.info()
        except libvirtError as error:
            log.exception("Exceptions: %s", error)
            return ret_storage_dict

        GB = 1024 * 1024 * 1024
        ret_storage_dict['size_total'] = float("%.3f" % (float(pool_info[1]) / GB))
        ret_storage_dict['size_free'] = float("%.3f" % (float(pool_info[3]) / GB))
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
        except libvirtError as e:
            log.debug(str(e))
            log.warn("Could not get memory info")
            return ret_mem_dict

        ret_mem_dict['size_total'] = float("%.3f" % (mem_info['total'] / 1024.0 / 1024.0))
        ret_mem_dict['size_free'] = float("%.3F" % (mem_info['free'] / 1024.0 / 1024.0))
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
        except libvirtError as e:
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

    def get_host_os(self, short_name=True):
        """
        :return: the host OS information. As no API to get host OS, return KVM/QEMU instead
        """
        log.warn('QEMU/KVM does not support to get host os, return kvm/qemu instead.')
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        xmlfile = self._hypervisor_handler.getCapabilities()
        if self.__is_kvm_available(xmlfile):
            return "KVM"
        else:
            return "QEMU"

    def get_templates_list(self):
        """
        :description get all the templates on host
        :return a list of tempaltes names
        """
        log.info("All powered-off VM can be used as a template. ")
        vm_list = self.get_vm_list()
        templist = [dom_name for dom_name in vm_list if self.is_instance_halted(dom_name)]
        return templist

    def is_instance_halted(self, inst_name):
        '''
        @param inst_name: instance name
        '''
        domain = self._get_domain_handler(inst_name)
        if not domain:
            log.debug("%s does not exist", inst_name)
            return False

        stats = domain.info()
        if stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_SHUTDOWN or stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_SHUTOFF:
            return True
        return False

    def get_vm_record(self, inst_name):
        """
        return the record dict for inst_name
        """
        handler = self.get_handler()
        try:
            dom = handler.lookupByName(inst_name)
        except libvirtError:
            return {}

        vm_record = {}
        if self.is_instance_running(inst_name=inst_name):
            vm_record['VCPUs_max'] = dom.maxVcpus()
        else:
            vm_record['VCPUs_max'] = 0

        vm_record['VCPUs_live'] = vm_record['VCPUs_max']
        vm_record['domid'] = dom.ID()
        vm_record['uuid'] = dom.UUIDString()
        vm_record['name_label'] = inst_name

        max_memory = dom.maxMemory() / 1024.0 / 1024.0
        vm_record['memory_dynamic_max'] = float("%.3f" % (float(max_memory)))
        vm_record['memory_dynamic_min'] = None
        vm_record['memory_static_max'] = float("%.3f" % (float(max_memory)))
        vm_record['memory_static_min'] = None

        #  dom.info() consist of the state, max memory,memory, cpus and cpu time for the domain.
        stats = dom.info()
        vm_record['memory_target'] = float("%.3f" % (stats[DOMAIN_INFO_MAX_MEM] / 1024.0 / 1024.0))
        vm_record['memory_actual'] = float("%.3f" % (stats[DOMAIN_INFO_MEM] / 1024.0 / 1024.0))
        vm_record['running'] = stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_RUNNING
        vm_record['halted'] = stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_SHUTDOWN or \
                              stats[DOMAIN_INFO_STATE] == libvirt.VIR_DOMAIN_SHUTOFF

        return  vm_record

    # Disk API
    def __get_disk_elements_list(self, inst_name):
        """
        :param inst_name:
        :return: a dict with key is disk index and value is disk xml element
        """
        if not self._hypervisor_handler:
            self._hypervisor_handler = self.get_handler()

        disk_dict = {}
        domain = self._get_domain_handler(domain_name=inst_name)
        if not domain:
            log.error("Domain %s doesn't exist, can not get interfaces information.", inst_name)
            return []

        tree = xmlEtree.fromstring(domain.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))
        disk_list = tree.findall("devices/disk[@device='disk']")
        for disk in disk_list:
            device_name = disk.find('target').get('dev')
            if device_name:
                disk_dict[device_name] = disk
        # a dict of disk element, sorted by disk/target/dev.
        return [disk_dict[key] for key in sorted(disk_dict)]

    def _get_all_vdisk_name(self, inst_name=None):
        """
        return a list off all virtual disk names for a domain when inst_name is None, else return all volume names
        """
        if inst_name:
            file_path = []
            all_disks = self.__get_disk_elements_list(inst_name)
            for disk_element in all_disks:
                source = disk_element.find('source')
                if source is not None:
                    file_path.append(source.get('file'))

            return [os.path.basename(path) for path in file_path]

        else:
            file_name = []
            if self._hypervisor_handler is None:
                self._hypervisor_handler = self.get_handler()
            for pool in self._hypervisor_handler.listAllStoragePools(libvirt.VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE):
                file_name.extend(pool.listVolumes()) #  listAllVolumes(flags=0) return list of object, flags is not used

            return file_name

    def _get_available_vdisk_name(self, inst_name):
        """
        :param inst_name:
        :return: a available virtual disk name for a domain, different from all the volume name in all pools
        """
        all_names = [str(filename).split(".")[0] for filename in filter(lambda x: inst_name in x, self._get_all_vdisk_name())]
        log.debug("all vdisk name with inst name :%s, %s", inst_name, all_names)
        nextindex = len(all_names)

        new_name = inst_name # + "-" + str(nextindex)
        while new_name in all_names:
            nextindex += 1
            new_name = inst_name+ "-" + str(nextindex)

        return new_name

    def _delete_volume_from_pool(self, volume_path):
        """
        :param volume_path:
        :return:
        """
        try:
            volobj = self._hypervisor_handler.storageVolLookupByPath(volume_path)
            volobj.wipe(0)
            volobj.delete(0)
        except libvirtError as error:
            log.debug("Error when delete volume: %s", volume_path)
            return False
        return True

    def add_vdisk_to_vm(self, inst_name, storage_name, size, disk_type="qcow2"):
        """
        @param inst_name: the name of VM
        @param storage_name: which storage repository the virtual disk put
        @param size: the disk size
        @:param disk_type: qcow, qcow2, vmdk, raw, vhd, fat, ext2/3/4, etc
        """
        if not self._hypervisor_handler:
            self._hypervisor_handler = self.get_handler()
        try:
            pool = self._hypervisor_handler.storagePoolLookupByName(storage_name)
        except libvirtError as error:
            log.error("No storage named: %s", storage_name)
            return False
        pool_free = pool.info()[-1] # pool.info is a list [Pool state, Capacity, Allocation, Available]
        if int(size) * (2**30) > pool_free:
            log.error("No such enough free size in storage %s", storage_name)
            return False

        pool_xml_tree = xmlEtree.fromstring(pool.XMLDesc())
        pool_path = pool_xml_tree.find("target/path")
        if pool_path is None:
            path_str = "/var/lib/libvirt/images" #  the default path for pool in kvm
        else:
            path_str = pool_path.text
        disk_name = "".join([self._get_available_vdisk_name(inst_name), ".", disk_type])
        target_vol_path = os.path.join(path_str, disk_name )

        # volume type: file, block, dir, network, netdir
        #'GB' (gigabytes, 10^9 bytes), 'G' or 'GiB' (gibibytes, 2^30 bytes)
        storage_vol_xml = """
        <volume type="file">
            <name>%s</name>
            <allocation>0</allocation>
            <capacity unit="G">%s</capacity>
            <target>
                <path>%s</path>
                <format type='%s'/>
                <permissions>
                    <owner>107</owner>
                    <group>107</group>
                    <mode>0644</mode>
                    <label>virt_image_t</label>
                </permissions>
            </target>
        </volume>"""

        storage_vol_xml = storage_vol_xml %(disk_name, size, target_vol_path, disk_type)
        vol_obj = pool.createXML(storage_vol_xml)

        return self.attach_disk_to_domain(inst_name, target_vol_path, disk_type)

    def clone_disk(self, source_file_path, target_disk_name):
        """
        :param source_file_path:
        :param target_disk_name:
        :return:
        """
        vol = self._hypervisor_handler.storageVolLookupByPath(source_file_path)
        format_element = xmlEtree.fromstring(vol.XMLDesc(0)).find("target/format")
        vol_format = format_element.get('type')
        vol_clone_xml = """
                        <volume>
                            <name>%s</name>
                            <capacity>0</capacity>
                            <allocation>0</allocation>
                            <target>
                                <format type='%s'/>
                                 <permissions>
                                    <owner>107</owner>
                                    <group>107</group>
                                    <mode>0644</mode>
                                    <label>virt_image_t</label>
                                </permissions>
                            </target>
                        </volume>""" %(target_disk_name, vol_format)
        log.info("Clone from %s to %s", source_file_path, target_disk_name)
        pool = vol.storagePoolLookupByVolume()
        new_vol = pool.createXMLFrom(vol_clone_xml, vol, 0) # only (name, perms) are passed for a new volume
        return new_vol

    def attach_disk_to_domain(self, inst_name, target_volume, disk_type):
        """
        add disk in xml definition
        :param inst_name:
        :param target_volume:
        :return:
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False
        xmlstr = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        tree =  xmlEtree.fromstring(xmlstr)
        device_elment = tree.find("devices")
        target_dev = [target.get("dev") for target in device_elment.findall("disk[@device='disk']/target")]

        virtio_dev = [dev[2:] for dev in filter(lambda x: "vd" in x, target_dev)]
        dev = "vd%c" %(ord(sorted(virtio_dev)[-1]) + 1 if virtio_dev else "a")

        disk_xml_str = """
        <disk type='file' device='disk'>
            <driver name='qemu' type='%s'/>
            <source file='%s'/> 
            <target dev='%s' bus='virtio'/>
        </disk>""" % (disk_type, target_volume, dev)
        disk_elment = xmlEtree.fromstring(disk_xml_str)
        device_elment.append(disk_elment)
        # new_xml = xmlEtree.tostring(tree)
        # ret = self._hypervisor_handler.defineXML(new_xml)
        if dom.isActive():
            ret = dom.attachDeviceFlags(disk_xml_str, libvirt.VIR_DOMAIN_AFFECT_LIVE|libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            ret = dom.attachDeviceFlags(disk_xml_str)
        return ret == 0

    def detach_disk_from_domain(self, inst_name, target_volume=None, force=False):
        """
        deactivate volume from pool, if force is True, physically remove the volume
        :param inst_name:
        :param target_volume: the full path name of disk file
        :param force: True to physically remove volume
        :return: True or False
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            log.error("No domain named %s.", inst_name)
            return False

        xmlstr = dom.XMLDesc()
        tree =  xmlEtree.fromstring(xmlstr)
        device_elment = tree.find("devices")
        disk_list = device_elment.findall("disk[@device='disk']")
        ret = None
        for disk_element in disk_list:
            source = disk_element.find("source")
            if source is None:
                continue
            else:
                file_path = source.get("file")
                if target_volume and file_path != target_volume:
                    continue
            log.info("Detach device: %s", file_path)
            if dom.isActive():
                ret = dom.detachDeviceFlags(xmlEtree.tostring(disk_element),
                                            libvirt.VIR_DOMAIN_AFFECT_LIVE|libvirt.VIR_DOMAIN_AFFECT_CONFIG)
            else:
                ret = dom.detachDeviceFlags(xmlEtree.tostring(disk_element))
            # remove disk from host
            if force and ret == 0:
                log.debug("Physically remove disk: %s", file_path)
                self._delete_volume_from_pool(file_path)
            if ret != 0:
                log.error("Detach disk [%s] from domain [%s] return %s", file_path, inst_name, ret)
                return False

        if ret is None:
            # no disk found in xml config
            log.error("No volume named %s in domain.", target_volume)
            return False
        else:
            return ret == 0

    def get_disk_size(self, inst_name, device_num):
        """
        :param inst_name: VM name
        :param device_num: the disk index number
        :return: return size in GB, or 0 if no device found
        """
        disk_list = self.__get_disk_elements_list(inst_name)
        try:
            disk_element = disk_list[int(device_num)]
        except IndexError:
            log.error("No disk found with device number: %s", device_num)
            return 0

        source = disk_element.find("source")
        if source is None:
            return 0

        file_path = source.get("file", None)
        try:
            volume_obj = self._hypervisor_handler.storageVolLookupByPath(file_path)
            # volume_list.info(): type, Capacity, Allocation(used)
            return volume_obj.info()[1]/1024.0/1024.0/1024.0
        except (TypeError, IndexError) as error:
            log.exception("Exceptions raise when get disk size: %s", error)
            return 0

    def get_all_disk(self, inst_name):
        """
        {'0': {'disk_size': 20.0, 'device_name': 'xvda'}, '3': {'disk_size': 0, 'device_name': 'xvdd'}}
        :param inst_name:
        :return: return a dict with infor about all the virtual disk number, eg, 1,2, etc and its name in guest, eg:vda
        """
        disk_list = self.__get_disk_elements_list(inst_name=inst_name)
        all_disk_info = {}
        for disk_num, disk_elment in enumerate(disk_list):
            device_name = disk_elment.find('target').get('dev')
            file_path = disk_elment.find('source').get('file')
            log.debug("Disks on domain [%s]: disk path: %s",inst_name, file_path)

            volume_info = self._hypervisor_handler.storageVolLookupByPath(file_path).info()
            disk_dize = volume_info[1]/1024.0/1024.0/1024.0
            disk_free = (volume_info[1] - volume_info[2])/1024.0/1024.0/1024.0
            disk_free = float("%.3f" %disk_free)

            all_disk_info[disk_num] = {'disk_size': disk_dize, 'device_name': device_name, 'disk_free': disk_free}

        return all_disk_info

    def allowed_set_vcpu_live(self, inst_name):
        """
        :param inst_name:
        :return: True if allowed to set vcpu lively, else False
        """
        return True

    def set_vm_vcpu_live(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a running VM;and set vcpus in the config file when domain is deactive
        :param inst_name:
        :param vcpu_num: should be str of a int number
        :return: True or False
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False

        vcpu_num = int(vcpu_num)
        if vcpu_num > self.get_vm_vcpu_max(inst_name):
            log.error("vCpus number [%s] exceed the limit of max vcpus: %s",vcpu_num, dom.maxVcpus())
            return False

        try:
            if dom.isActive():
                # dom.setVcpus(vcpu_num) # only effect the live domain, when power off, the config lose
                ret = dom.setVcpusFlags(vcpu_num, libvirt.VIR_DOMAIN_AFFECT_LIVE|libvirt.VIR_DOMAIN_AFFECT_CONFIG)
            else:
                ret = dom.setVcpusFlags(vcpu_num, libvirt.VIR_DOMAIN_AFFECT_CURRENT)
        except libvirtError as error:
            log.exception("Exceptions when set vcpu lively: %s", error)
            return False

        return ret == 0

    def set_vm_vcpu_max(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a halted VM; when vm is active, the setting will take effect when next reboot
        :param inst_name:
        :param vcpu_num:
        :return: True or False
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False

        vcpu_num = int(vcpu_num)
        try:
            # Flag 'VIR_DOMAIN_AFFECT_CONFIG' is required by flag 'VIR_DOMAIN_VCPU_MAXIMUM'
            ret = dom.setVcpusFlags(vcpu_num, libvirt.VIR_DOMAIN_AFFECT_CONFIG|libvirt.VIR_DOMAIN_VCPU_MAXIMUM)
        except libvirtError as error:
            log.exception("Exception when set vcpu max: %s", error)
            return False

        return ret == 0

    def __get_vcpu_from_xml(self, xml_str):
        """
        if no current vcpus in xml, return max vcpus as current vcpus
        :param xml_str:
        :return: (max vcpus, current vcpus)
        """
        xmltree = xmlEtree.fromstring(xml_str)
        vcpu = xmltree.find('vcpu')
        if vcpu is None:
            log.error("No vcpu element found in XML description.")
            return (0, 0)
        else:
            try:
                max = int(vcpu.text)
                current = vcpu.get("current", max)
            except ValueError:
                max, current = 0, 0
            return (max, current)

    def get_vm_vcpu_current(self, inst_name):
        """
        :return: the current vcpu number or 0
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return 0

        _, current_vcpu= self.__get_vcpu_from_xml(dom.XMLDesc())
        return current_vcpu

    def get_vm_vcpu_max(self, inst_name):
        """
        :param inst_name:
        :return: max cpu number or 0
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return 0
        if not dom.isActive():
            return self.__get_vcpu_from_xml(dom.XMLDesc())[0]
        else:
            return dom.maxVcpus()

    def get_host_name(self):
        """
        The server name, in kvm it is hostname.
        :return: (name_label, hostname)
        """
        if not self._hypervisor_handler:
            self._hypervisor_handler = self.get_handler()

        hostname = self._hypervisor_handler.getHostname()
        return (hostname, hostname)

    def set_vm_static_memory(self, inst_name, memory_max=None, memory_min=None):
        """
        set memory for a inactive domain
        :param inst_name:
        :param memory_max: size of GB
        :param memory_min: size of GB
        :return:
        """
        # dom.setMaxMemory() need dom to be inactive
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False
        if dom.isActive():
            log.error("Set domain max memory need it to be stopped.")
            return False

        gitabyte = 1024 * 1024 # unit is KB
        if memory_max:
            memory_size = int(memory_max) * gitabyte
        elif memory_min:
            memory_size = int(memory_min) * gitabyte
        else:
            log.error("Neither maxMemory nor minMemory is supplied.")
            return False
        # dom.setMemoryFlags(memory_size, libvirt.VIR_DOMAIN_AFFECT_CURRENT|libvirt.VIR_DOMAIN_MEM_MAXIMUM) also OK
        ret = dom.setMaxMemory(memory_size)
        return ret == 0

    def set_vm_dynamic_memory(self, inst_name, memory_max=None, memory_min=None):
        """
        set memory for a domain, if it is active, set it lively and the config file, if it is deactive, set the config file
        :param inst_name:
        :param max_memory:
        :param min_memory:
        :return:
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False
        gitabyte = 1024 * 1024 # unit is KB
        if memory_max:
            memory_size = int(memory_max) * gitabyte
        elif memory_min:
            memory_size = int(memory_min) * gitabyte
        else:
            log.error("Neither maxMemory nor minMemory is supplied.")
            return False
        #
        if dom.isActive():
            ret = dom.setMemoryFlags(memory_size, libvirt.VIR_DOMAIN_AFFECT_LIVE|libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            ret =dom.setMemoryFlags(memory_size) # dom.setMemory need dom to be active

        return ret == 0

    def set_vm_memory_live(self, inst_name, memory_target):
        """
        :param memory_target: Memory in GB
        :return:
        """
        dom = self._get_domain_handler(domain_name=inst_name)
        if dom is None:
            return False
        if not dom.isActive():
            log.error("Set domain memory lively need it to be running.")
            return False

        memory_size = int(memory_target) * 1024 * 1024  # memory in KB
        ret = dom.setMemoryFlags(memory_size, libvirt.VIR_DOMAIN_AFFECT_LIVE|libvirt.VIR_DOMAIN_AFFECT_CONFIG)

        return ret == 0

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    (options, args) = parser.parse_args()
    virt = QemuVirtDriver(hostname=options.host, user=options.user, passwd=options.passwd)
    filebeat = virt._get_domain_handler("filebeat")
    test = virt._get_domain_handler("test")
    # print virt.set_vm_vcpu_max("filebeat", 5)
    #print virt.set_vm_vcpu_live("test", 3)
    # print virt.get_disk_size(inst_name="test", device_num=0)
    # print virt.get_all_disk(inst_name="test")
    pool = virt._hypervisor_handler.storagePoolLookupByName("default")
    for vol in  pool.listAllVolumes():
        if "test-1.qcow2" == vol.name():
            break
    # vol_obj= virt.add_vdisk_to_vm("test", "default",2)
    # virt._delete_volume_from_pool("/var/lib/libvirt/images/test-6.qcow2")
    # virt.attach_disk_to_domain("test", "/var/lib/libvirt/images/test-1.qcow2", "qcow2")
    # virt.attach_disk_to_domain("test", "/var/lib/libvirt/images/test.qcow2", "qcow2" )
    # virt.detach_disk_from_domain("test", "/var/lib/libvirt/images/test-5.qcow2")
    # print virt.detach_disk_from_domain("test")
    # print test.XMLDesc()
    # print test.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)

     # vol = virt.clone_disk("/var/lib/libvirt/images/test-7.qcow2", "clone-disk.qcow2")
    # ret = virt.create_instance("new_vm", "CentOS7Mini")

    # print ret
    # virt.power_on_vm("new_vm")

    virt.delete_instance("new_vm", True)
