#!/usr/bin/env python
#! -*- coding: utf-8 -*-
#########################################################################
# File Name: Xen/virt_driver_xen.py
# Attentions: provide command API for operations on Xenserver VMs, not using libvirtd
# Author: longhui
# Note: Please alternatively add params checking when use those API
# Created Time: 2018-02-08 11:34:12
#########################################################################

import time
from lib.Log.log import log
from lib.Val.virt_driver import VirtDriver
from lib.Val.Xen import XenAPI

API_VERSION_1_1 = '1.1'


class XenVirtDriver(VirtDriver):
    '''
    '''

    def __init__(self, hostname=None, user="root", passwd=""):
        VirtDriver.__init__(self, hostname, user, passwd)
        self._hypervisor_handler = None

        self._hypervisor_handler = self.get_handler()

    def __del__(self):
        try:
            if self._hypervisor_handler is not None:
                log.debug("Release handler in virt driver, ID:%s", id(self._hypervisor_handler))
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

        log.debug("Get handler in virt driver, ID:%s", id(self._hypervisor_handler))
        return self._hypervisor_handler

    def delete_handler(self):
        '''
        release the session
        '''
        try:
            if self._hypervisor_handler is not None:
                log.debug("Release handler manually in virt driver, ID:%s", id(self._hypervisor_handler))
                self._hypervisor_handler.xenapi.session.logout()
                self._hypervisor_handler = None
        except Exception, error:
            log.debug(error)

    def get_vm_list(self):
        """
        Return the VMs from system
        """
        handler = self.get_handler()
        if handler is not None:
            vms = handler.xenapi.VM.get_all_records()
            vm_instances = filter(lambda x:x['is_a_template'] == False and
                                         x['is_control_domain'] == False, vms.values())
            vm_names = [vm['name_label'] for vm in vm_instances]
            return vm_names
        else:
            log.error("Cann't get handler while get all vm list.")
            return []

    def get_templates_list(self):
        '''
        return all templates ref list
        '''
        handler = self.get_handler()
        if handler is not None:
            vms = handler.xenapi.VM.get_all_records()
            vm_templates = filter(lambda x: x['is_a_template'] == True, vms.values())
            vm_names = [vm['name_label'] for vm in vm_templates]
            return vm_names
        else:
            log.error('Can not connect to xenServer when try to get templates list.')
            return []

    def is_instance_exists(self, inst_name):
        '''
        @note Object name_label fields are not guaranteed to be unique and so the get_by_name_label
        API call returns a set of references rather than a single reference.
        '''
        return inst_name in self.get_vm_list()

    def is_instance_running(self, inst_name):
        '''
        VM states including:Halted, Paused, Running, Suspended
        '''
        if not self.is_instance_exists(inst_name):
            log.error("Instance with name %s doesn't exist.", inst_name)
            return False

        handler = self.get_handler()
        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        record = handler.xenapi.VM.get_record(vm_ref)

        return record['power_state'] == 'Running'

    def is_instance_halted(self, inst_name):
        """
        VM is offline and not using any resources
        """
        if not self.is_instance_exists(inst_name):
            log.error("Instance with name %s doesn't exist.", inst_name)
            return False

        handler = self.get_handler()
        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        record = handler.xenapi.VM.get_record(vm_ref)

        return record['power_state'] == 'Halted'

    def create_instance(self, inst_name, reference_vm):
        '''
        @see: VM ref clone (session ref session_id, VM ref vm, string new_name)
        @see: void provision (session ref session_id, VM ref vm)
        '''
        handler = self.get_handler()
        try:
            log.debug("Start to copy templates:%s", reference_vm)
            templ_ref = handler.xenapi.VM.get_by_name_label(reference_vm)[0]  #get_by_name_label return a list
            new_vm_ref = handler.xenapi.VM.clone(templ_ref, inst_name)
            handler.xenapi.VM.provision(new_vm_ref)
        except Exception, error:
            log.exception("Exception: %s while create VM [%s].", error, inst_name)
            return False

        return True

    def delete_instance(self, inst_name):
        """
        @see void destroy (session ref session_id, VM ref self), This function can
            only be called when the VM is in the Halted State.
        """
        try:
            self.power_off_vm(inst_name)
            log.info("Start destroying vm [%s].", inst_name)

            handler = self.get_handler()
            if handler is not None:
                vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
                handler.xenapi.VM.destroy(vm_ref)
                return True
            else:
                log.error("Cann't get handler while destroy vm [%s].", inst_name)
                return False
        except Exception, error:
            log.exception("Exception: %s raised when destory vm [%s].", error, inst_name)
            return False

    def power_off_vm(self, inst_name):
        """
        @see: void shutdown (session ref session_id, VM ref vm), it will attempts to
        first clean shutdown a VM and if it should fail then perform a hard shutdown on it.
        """
        log.debug("Start power off vm [%s].", inst_name)
        if self.is_instance_halted(inst_name):
            log.info("VM [%s] is already not running.", inst_name)
            return True

        handler = self.get_handler()
        if handler is None:
            log.error("Can not get handler when try to power off VM [%s].", inst_name)
            return False

        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]

        try:
            handler.xenapi.VM.shutdown(vm_ref)
            time.sleep(1)
        except Exception, error:
            log.exception("Exception raised: %s when shutdown VM [%s].", error, inst_name)
            return False

        return True

    def power_on_vm(self, inst_name):
        """
        @summary: power on vm with name label inst_name
        """
        log.debug("Start power on VM [%s].", inst_name)
        if self.is_instance_running(inst_name):
            log.info("VM [%s] is already running.", inst_name)
            return True

        handler = self.get_handler()
        if handler is not None:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            vm_state = handler.xenapi.VM.get_record(vm_ref)['power_state']
            try:
                if vm_state == "Suspended":
                    handler.xenapi.VM.resume(vm_ref, False, True)  # start_paused = False; force = True
                elif vm_state == "Paused":
                    handler.xenapi.VM.unpause(vm_ref)
                else:  #vm_state == "Halted"
                    handler.xenapi.VM.start(vm_ref, False, True)
                time.sleep(2)
            except Exception, error:
                log.error("Raise exception:'%s' while power on vm:%s", error, inst_name)
                return False
        else:
            log.error("Cann't get handler when power on vm:%s", inst_name)
            return False

        return True

    def reboot(self, inst_name):
        """
        @see: void clean_reboot (session ref session_id, VM ref vm)
        @note: This can only be called when the specified VM is in the Running state
        """
        if not self.is_instance_running(inst_name):
            log.error("Only a running VM can be rebooted.")
            return False

        handler = self.get_handler()
        if handler is None:
            log.error("Can not get handler when reboot VM [%s].", inst_name)
            return False

        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        try:
            handler.xenapi.VM.clean_reboot(vm_ref)
            time.sleep(2)
        except Exception, error:
            log.exception("Exception: %s when reboot VM [%s].", error, inst_name)
            return False

        return True

    #####  VM informations api ######
    def _get_vm_ref(self, inst_name):
        """
        @param inst_name: vm instance name
        @return: return a reference object to the vm
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()
        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
        except Exception, error:
            log.exception("Raise exceptions when get vm reference: [%s].", error)
            return None
        return vm_ref

    def get_vm_record(self, inst_name):
        """
        return the record dict for inst_name
        """
        handler = self.get_handler()

        record = {}
        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            record = handler.xenapi.VM.get_record(vm_ref)
        except Exception, error:
            log.exception("Exception: %s when get record for VM [%s].", error, inst_name)
            return {}

        return record

    def get_vm_guest_metrics_record(self, inst_name):
        """
        return a dict with networks, os_version, uuid, memory, etc as keys
        'network':{'0/ip': '10.143.248.80', '0/ipv6/0': 'fe80::b8d9:89ff:fef3:b252'}
        'os_version': {'distro': 'centos',  'major': '7',  'minor': '1',
                       'name': 'CentOS Linux release 7.1.1503 (Core)',
                       'uname': '3.10.0-229.4.2.el7.x86_64'},
        """
        handler = self.get_handler()
        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            guest_metrics_ref = handler.xenapi.VM.get_guest_metrics(vm_ref)
            return handler.xenapi.VM_guest_metrics.get_record(guest_metrics_ref)
        except Exception, error:
            log.exception("Exceptions raised:%s", error)
            return {}

    def _get_available_device_num(self, inst_name):
        """
        return a device number which is not used
        """
        handler = self.get_handler()
        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        all_vdbs = handler.xenapi.VM.get_VBDs(vm_ref)
        device_list = []
        for vdb_ref in all_vdbs:
            device = handler.xenapi.VBD.get_userdevice(vdb_ref)
            device_list.append(int(device))
        max_num = max(device_list)
        for i in range(max_num + 1):
            if i not in device_list:
                return str(i)
        allowed_vbds = handler.xenapi.get_allowed_VBD_devices(vm_ref)
        if str(max_num + 1) not in allowed_vbds:
            log.error("No avaiable VBD device to be allocated on VM [%s.]", inst_name)
            return ""

        return str(max_num + 1)

    def add_vdisk_to_vm(self, inst_name, storage_name, size):
        """
        @param inst_name: the name of VM
        @param storage_name: which storage repository the virtual disk put
        @param size: the disk size
        """
        handler = self.get_handler()
        userdevice = self._get_available_device_num(inst_name)
        if not userdevice:
            return False

        log.info("Start to add virtual disk [%s] to VM: [%s]", userdevice, inst_name)

        name_description = "VDI created by API, on VM: %s, SR: %s" % (inst_name, storage_name)
        record = {"name_label": inst_name + " data " + userdevice, "name_description": name_description}
        try:
            sr_ref = handler.xenapi.SR.get_by_name_label(storage_name)[0]
        except Exception, error:
            log.exception("No storage named [%s], exception: %s", storage_name, error)
            return False

        record["SR"] = sr_ref
        record["virtual_size"] = str(int(size) * 1024 * 1024 * 1024)  #size GB
        record['type'] = "user"
        record['read_only'] = False
        record['sharable'] = False
        record["other_config"] = {}
        try:
            vdi_ref = handler.xenapi.VDI.create(record)
        except Exception, error:
            log.error("Create VDI raise error:[%s]", error)
            return False

        vbd_record = {"VDI":vdi_ref, 'other_config': {}, 'mode': 'RW', 'type': 'Disk',
                      'empty': False, 'qos_algorithm_type': '', 'qos_algorithm_params': {}}
        vbd_record['userdevice'] = str(userdevice)
        vbd_record['bootable'] = False

        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            vbd_record['VM'] = vm_ref
            vbd_ref = handler.xenapi.VBD.create(vbd_record)
            time.sleep(1)
            log.info("Waiting for the virtual disk plug in...")
            sleep_time = 0
            while((handler.xenapi.VBD.get_device(vbd_ref) == '') and (sleep_time < 10)):
                log.debug("wait device [%s] to plug in, sleep time %s.", handler.xenapi.VBD.get_device(vbd_ref), sleep_time)
                handler.xenapi.VBD.plug(vbd_ref)
                time.sleep(2)
                sleep_time += 2
        except Exception, error:
            log.exception("Exception when create VBD: %s.", error)
            return False

        return True

    ####    Host information  API  ####
    def get_host_cpu_info(self):
        """
        Return HV CPU info: cpu speed: MHZ;
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        ret_cpu_dict = {}
        try:
            host_ref = self._hypervisor_handler.xenapi.host.get_all()[0]
            cpu_info = self._hypervisor_handler.xenapi.host.get_cpu_info(host_ref)

            ret_cpu_dict['cpu_model'] = cpu_info.get('model', "")
            ret_cpu_dict['cpu_modelname'] = cpu_info.get('modelname', "")
            ret_cpu_dict['cpu_cores'] = cpu_info.get("cpu_count", 0)
            ret_cpu_dict['cpu_speed'] = cpu_info.get('speed', "0")
            ret_cpu_dict['cpu_sockets'] = cpu_info.get("socket_count", 0)
        except Exception, error:
            log.exception("Exceptions when get host cpu infor: %s", error)
            return ret_cpu_dict

        return ret_cpu_dict

    def get_host_all_storages(self):
        """
        return a list of all the storage names
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        ret_storage_list = []
        try:
            all_storage = self._hypervisor_handler.xenapi.SR.get_all()
            ret_storage_list = [self._hypervisor_handler.xenapi.SR.get_name_label(sr_ref) for sr_ref in all_storage]
        except Exception, error:
            log.exception("Exception when get all storage info:%s", error)

        return ret_storage_list

    def get_host_storage_info(self, storage_name="Local storage"):
        """
        Return HV storage info: Unit is GB
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        ret_storage_dict = {}
        try:
            sr_ref = self._hypervisor_handler.xenapi.SR.get_by_name_label(storage_name)[0]
        except  Exception, error:
            log.exception("No storage repository named: [%s], %s", storage_name, error)
            return ret_storage_dict

        total = self._hypervisor_handler.xenapi.SR.get_physical_size(sr_ref)
        used = self._hypervisor_handler.xenapi.SR.get_physical_utilisation(sr_ref)
        ret_storage_dict['size_total'] = int(total) / 1024 / 1024 / 1024
        ret_storage_dict['size_used'] = int(used) / 1024 / 1024 / 1024
        ret_storage_dict['size_free'] = (int(total) - int(used)) / 1024 / 1024 / 1024
        return ret_storage_dict

    def get_host_mem_info(self):
        """
        Return HV memory info: Unit is MB
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        ret_mem_dict = {}
        try:
            host_ref = self._hypervisor_handler.xenapi.host.get_all()[0]
            host_metrics_ref = self._hypervisor_handler.xenapi.host.get_metrics(host_ref)
            total = self._hypervisor_handler.xenapi.host_metrics.get_memory_total(host_metrics_ref)
            free = self._hypervisor_handler.xenapi.host_metrics.get_memory_free(host_metrics_ref)
        except Exception, error:
            log.exception("Exception raised when get host memory infor:%s", error)
            return ret_mem_dict

        ret_mem_dict['size_total'] = int(total) / 1024 / 1024
        ret_mem_dict['size_free'] = int(free) / 1024 / 1024
        ret_mem_dict['size_used'] = (int(total) - int(free)) / 1024 / 1024
        return ret_mem_dict

    def get_host_sw_ver(self, short_name=True):
        """
        Return the HV SW version
        """
        hv_handler = self.get_handler()

        try:
            host_ref = hv_handler.xenapi.host.get_all()[0]
            soft_record = hv_handler.xenapi.host.get_software_version(host_ref)

            if short_name:
                return "xapi: %s" % soft_record['xapi']
            else:
                return "xen: %s, xapi: %s" % (soft_record['xen'], soft_record['xapi'])
        except Exception, error:
            log.exception("Exceptions: %s", error)
            return ""

    def get_host_plat_info(self):
        """
        Return HV platform info
        This needs root permission to do
        """
        ret_plat_dict = {}
        handler = self.get_handler()
        try:
            host_ref = handler.xenapi.host.get_all()[0]
            bios_info = handler.xenapi.host.get_bios_strings(host_ref)
            ret_plat_dict['vendor_name'] = bios_info.get('system-manufacturer', "")
            ret_plat_dict['product_name'] = bios_info.get('system-product-name', "")
            ret_plat_dict['serial_number'] = bios_info.get('system-serial-number', "")
        except Exception, error:
            log.error("Exception when get host platform infor:%s", error)

        return ret_plat_dict


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 1 and len(sys.argv) != 4:
        print "Usage:"
        print sys.argv[0], "[host-ip user passwd]"
        sys.exit(1)
    if len(sys.argv) == 4:
        ip = sys.argv[1]
        user = sys.argv[2]
        passwd = str(sys.argv[3]).replace('\\', '')
    else:
        ip = None
        user = "root"
        passwd = ""
    log.info("test log")
    virt = XenVirtDriver(ip, user, passwd)
    handler = virt.get_handler()
    vm_list = virt.get_vm_list()
    print vm_list
    for vm in vm_list:
        record = virt.get_vm_record(vm)
        if record:
            log.info("%s %s %s", vm, record['uuid'], record['name_label'])
    vm_name = "new_vm"
    if virt.is_instance_exists(vm_name):
        ret = virt.power_off_vm(vm_name)
        if not ret:
            log.error("Can not power off VM[%s]", vm_name)
        ret = virt.delete_instance(vm_name)
        if not ret:
            log.error("delete vm failed: %s", vm_name)
        else:
            log.info("delete vm successfully.")

    ret = virt.create_instance(vm_name, r"CentOS 7.2 for Lain")
    if ret:
        ret = virt.power_on_vm(vm_name)
        if ret:
            log.success("Power on vm successfully.")
        else:
            log.fail("Power on VM failed.")
    else:
        log.fail("Can not create new VM.")
    print ret

