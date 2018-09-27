#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################################
# File Name: Xen/virt_driver_xen.py
# Attentions: provide command API for operations on Xenserver VMs, not using libvirtd
# Author: longhui
# Note: Please alternatively add params checking when use those API
# Created Time: 2018-02-08 11:34:12
#########################################################################

import signal
import time

from lib.Log.log import log
from lib.Val.Xen import XenAPI
from lib.Val.virt_driver import VirtDriver


API_VERSION_1_1 = '1.1'


class XenVirtDriver(VirtDriver):
    '''
    '''

    def __init__(self, hostname=None, user="root", passwd=""):
        VirtDriver.__init__(self, hostname, user, passwd)

        self._hypervisor_handler = self.get_handler()

    def __del__(self):
        try:
            if self._hypervisor_handler is not None:
                log.debug("Release handler in virt driver, ID:%s", id(self._hypervisor_handler))
                self._hypervisor_handler.xenapi.session.logout()
                self._hypervisor_handler = None
        except Exception as error:
            log.debug(error)

    def get_handler(self):
        '''
        return the handler of the virt_driver
        '''
        if self._hypervisor_handler is not None:
            return self._hypervisor_handler

        if self.hostname is None:
            self._hypervisor_handler = XenAPI.xapi_local()  # no __nonzero__, can not use if/not for bool test
        else:
            log.debug("connecting to %s with user:%s,passwd:%s", "http://" + str(self.hostname), self.user, self.passwd)
            self._hypervisor_handler = XenAPI.Session("http://" + str(self.hostname))

        old = signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(4)  # connetctions timeout set to 5 secs
        try:
            self._hypervisor_handler.xenapi.login_with_password(self.user, self.passwd, API_VERSION_1_1,
                                                                'XenVirtDriver')
        except Exception as error:
            log.warn("Exception raised: %s when get handler.", error)
            log.info("Retry connecting to :%s", "https://" + str(self.hostname))
            self._hypervisor_handler = XenAPI.Session("https://" + str(self.hostname))

            signal.alarm(4)
            try:
                self._hypervisor_handler.xenapi.login_with_password(self.user, self.passwd, API_VERSION_1_1,
                                                                    'XenVirtDriver')
            except Exception as errors:
                log.exception("Exception errors:%s when get handler", errors)
                return None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

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
        except Exception as error:
            log.debug(error)

    def get_vm_list(self):
        """
        Return the VMs from system
        """
        handler = self.get_handler()
        if handler is not None:
            vms = handler.xenapi.VM.get_all_records()
            vm_instances = filter(lambda x: x['is_a_template'] == False and
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

    # TODO
    def create_instance(self, inst_name, reference_vm, storage_pool=None):
        '''
        VM.clone doesn't support tartget storage, VM.copy support a new SR. Clone automatically exploits the capabilities
        of the underlying storage repository in which the VM's disk images are stored (e.g. Copy on Write).
        copy guarantees that the disk images of the newly created VM will be 'full disks' - i.e. not part of a CoW chain
        @:param storage_pool: the storage in which new VM will be put
        @see: VM ref clone (session ref session_id, VM ref vm, string new_name)
        @see: void provision (session ref session_id, VM ref vm)
        '''
        handler = self.get_handler()
        try:
            log.debug("Start to copy templates:%s", reference_vm)
            templ_ref = handler.xenapi.VM.get_by_name_label(reference_vm)[0]  # get_by_name_label return a list
            new_vm_ref = handler.xenapi.VM.clone(templ_ref, inst_name)
            handler.xenapi.VM.provision(new_vm_ref)
        except Exception as error:
            log.exception("Exception: %s while create VM [%s].", error, inst_name)
            return False

        return True

    def delete_instance(self, inst_name):
        """
        @see void destroy (session ref session_id, VM ref self), This function can
            only be called when the VM is in the Halted State.
        """
        try:
            log.info("Try to power off vm [%s].", inst_name)
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
        except Exception as error:
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
            time.sleep(0.5)
        except Exception as error:
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
                else:  # vm_state == "Halted"
                    handler.xenapi.VM.start(vm_ref, False, True)
                time.sleep(1)
            except Exception as error:
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
        except Exception as error:
            log.exception("Exception: %s when reboot VM [%s].", error, inst_name)
            return False

        return True

    # Set VM static, dynamic memory
    def set_vm_static_memory(self, inst_name, memory_max=None, memory_min=None):
        """
        :param inst_name:
        :param memory_max: size of GB
        :param memory_min: size of GB
        :return:
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        if not memory_max and not memory_min:
            log.info("No memory size given, return...")
            return True

        if not self.is_instance_halted(inst_name=inst_name):
            log.error("Set static memory need VM to be halted.")
            return False
        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            gb = 1024.0 * 1024.0 * 1024.0
            if memory_max:
                memory_max = int(gb * float(memory_max))
                self._hypervisor_handler.xenapi.VM.set_memory_static_max(vm_ref, str(memory_max))
            if memory_min:
                memory_min = int(gb * float(memory_min))
                self._hypervisor_handler.xenapi.VM.set_memory_static_min(vm_ref, str(memory_min))

            return True
        except Exception as error:
            log.exception("Exception raise when set static min memory: %s", error)
            return False

    def set_vm_dynamic_memory(self, inst_name, memory_max=None, memory_min=None):
        """
        :param inst_name:
        :param memory_max:
        :param memory_min:
        :return:
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        # both a running or halted vm, set dynamic memory is supported. but it take a few while when vm is running
        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            gb = 1024.0 * 1024.0 * 1024.0
            if memory_max and memory_min:
                memory_max = int(gb * float(memory_max))
                memory_min = int(gb * float(memory_min))
                self._hypervisor_handler.xenapi.VM.set_memory_dynamic_range(vm_ref, str(memory_min), str(memory_max))
            elif memory_max:
                memory_max = int(gb * float(memory_max))
                self._hypervisor_handler.xenapi.VM.set_memory_dynamic_max(vm_ref, str(memory_max))
            elif memory_min:
                memory_min = int(gb * float(memory_min))
                self._hypervisor_handler.xenapi.VM.set_memory_dynamic_min(vm_ref, str(memory_min))
            else:
                log.info("No memory size given, return...")

            return True
        except Exception as error:
            log.exception("Exception raise when set static min memory: %s", error)
            return False

    def set_vm_memory_live(self, inst_name, memory_target):
        """
        :param memory_target: Memory in GB, set dynamic_max and dynamic_min to the target size
        :return:
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        if not self.is_instance_running(inst_name=inst_name):
            log.error("Set live memory need VM to be running.")
            return False
        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            gb = 1024.0 * 1024.0 * 1024.0
            memory_size = int(gb * float(memory_target))
            # set_memory_target_live has been deprecated
            # self._hypervisor_handler.xenapi.VM.set_memory_target_live(vm_ref, str(memory_size))
            self._hypervisor_handler.xenapi.VM.set_memory_dynamic_range(vm_ref, str(memory_size), str(memory_size))

            return True
        except Exception as error:
            log.exception("Exception raise when set live memory: %s", error)
            return False

    #  ## Set or GET VM VCPU number###
    def allowed_set_vcpu_live(self, inst_name):
        """
        :param inst_name:
        :return: True if allowed to set vcpu lively, else False
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()
        try:
            vm_ref = self._hypervisor_handler.xenapi.get_by_name_label(inst_name)[0]
            record = self._hypervisor_handler.xenapi.VM.get_record(vm_ref)
            if "changing_VCPUs_live" in record['allowed_operations']:
                return True
            else:
                return False
        except Exception:
            return False

    def set_vm_vcpu_live(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a running VM
        :param inst_name:
        :param vcpu_num: should be str of a int number
        :return: True or False
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            cpu_max = self._hypervisor_handler.xenapi.VM.get_VCPUs_max(vm_ref)
            if int(vcpu_num) > int(cpu_max):
                log.warn("VCPU number exceed the max cpu number:%s, will set it to the max instead.", cpu_max)
                vcpu_num = cpu_max
            self._hypervisor_handler.xenapi.VM.set_VCPUs_number_live(vm_ref, str(vcpu_num))
            return True
        except Exception as error:
            log.exception("Raise exceptions: [%s].", error)
            return False

    def set_vm_vcpu_max(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a halted VM
        :param inst_name:
        :param vcpu_num:
        :return: True or False
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        vcpu_num = int(vcpu_num)
        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            # 0 < VCPUs_at_startup <= VCPUs_max
            cpu_at_start = self._hypervisor_handler.xenapi.VM.get_VCPUs_at_startup(vm_ref)
            if vcpu_num < int(cpu_at_start):
                log.warn("The max cpu number is smaller than the live number [%s] and will change live cpu to it.",
                         cpu_at_start)
                self._hypervisor_handler.xenapi.VM.set_VCPUs_at_startup(vm_ref, str(vcpu_num))

            self._hypervisor_handler.xenapi.VM.set_VCPUs_max(vm_ref, str(vcpu_num))
            return True
        except Exception as error:
            log.exception("Raise exceptions: [%s].", error)
            return False

    def get_vm_vcpu_current(self, inst_name):
        """
        :return: the current vcpu number or 0
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            cpu_live = self._hypervisor_handler.xenapi.VM.get_VCPUs_at_startup(vm_ref)
            return int(cpu_live)
        except Exception as error:
            log.exception("Raise exceptions: [%s].", error)
            return 0

    def get_vm_vcpu_max(self, inst_name):
        """
        :param inst_name:
        :return: max cpu number or 0
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            vm_ref = self._hypervisor_handler.xenapi.VM.get_by_name_label(inst_name)[0]
            cpu_max = self._hypervisor_handler.xenapi.VM.get_VCPUs_max(vm_ref)
            return int(cpu_max)
        except Exception as error:
            log.exception("Raise exceptions: [%s].", error)
            return 0

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
        except Exception as error:
            log.exception("Raise exceptions when get vm reference: [%s].", error)
            return None
        return vm_ref

    def get_vm_record(self, inst_name):
        """
        return the record dict for inst_name
        """
        handler = self.get_handler()

        vm_record = {}
        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            record = handler.xenapi.VM.get_record(vm_ref)
        except Exception as error:
            log.exception("Exception: %s when get record for VM [%s].", error, inst_name)
            return {}

        GB = 1024 ** 3
        vm_record['VCPUs_max'] = record.get('VCPUs_max', None)
        vm_record['VCPUs_live'] = record.get('VCPUs_at_startup', None)
        vm_record['domid'] = record.get('domid', None)
        vm_record['uuid'] = record.get('uuid', None)
        vm_record['name_label'] = inst_name
        vm_record['memory_dynamic_max'] = float("%.3f" % (float(record.get('memory_dynamic_max', '0')) / GB))
        vm_record['memory_dynamic_min'] = float("%.3f" % (float(record.get('memory_dynamic_min', '0')) / GB))
        vm_record['memory_static_max'] = float("%.3f" % (float(record.get('memory_static_max', '0')) / GB))
        vm_record['memory_static_min'] = float("%.3f" % (float(record.get('memory_static_min', '0')) / GB))
        # current target for memory available to this VM
        vm_record['memory_target'] = float("%.3f" % (float(record.get("memory_target", 0)) / GB))
        try:
            guest_metrics = handler.xenapi.VM.get_metrics(vm_ref)
            memory_actual = handler.xenapi.VM_metrics.get_memory_actual(guest_metrics)
            vm_record['memory_actual'] = float("%.3f" % (float(memory_actual) / GB))
        except Exception as error:
            vm_record['memory_actual'] = vm_record['memory_target']
        vm_record['running'] = record['power_state'] == 'Running'
        vm_record['halted'] = record['power_state'] == 'Halted'

        return vm_record

    def get_os_type(self, inst_name, short_name=True):
        """
        get the os type, return string
        """
        guest_metrics = self._get_vm_guest_metrics_record(inst_name)
        if not guest_metrics:
            return None
        os_infor = guest_metrics.get('os_version', {})
        if short_name:
            return ".".join([os_infor.get('distro', 'Unknown'), os_infor.get('major', '0'), os_infor.get('minor', '0')])
        else:
            return os_infor.get('name', 'Unknown')

    def _get_vm_guest_metrics_record(self, inst_name):
        """
        return a dict with networks, os_version, uuid, memory, etc as keys
        'network':{'0/ip': '192.168.1.80', '0/ipv6/0': 'fe80::b8d9:89ff:fef3:b252'}
        'os_version': {'distro': 'centos',  'major': '7',  'minor': '1',
                       'name': 'CentOS Linux release 7.1.1503 (Core)',
                       'uname': '3.10.0-229.4.2.el7.x86_64'},
        """
        handler = self.get_handler()
        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            guest_metrics_ref = handler.xenapi.VM.get_guest_metrics(vm_ref)
            return handler.xenapi.VM_guest_metrics.get_record(guest_metrics_ref)
        except Exception as error:
            log.debug("Exceptions raised when get vm guest metrics:%s", error)
            return {}

    def _get_vm_metrics_record(self, inst_name):
        """
        :return: a dict as :{'VCPUs_number': '8', 'memory_actual': '1073741824', 'VCPUs_params': {},
                'VCPUs_utilisation': {'0': 0.0}}
        """
        handler = self.get_handler()
        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            vm_metrics_ref = handler.xenapi.VM.get_metrics(vm_ref)
            return handler.xenapi.VM_metrics.get_record(vm_metrics_ref)
        except Exception as error:
            log.exception("Exceptions raised:%s", error)
            return {}

    def _get_available_device_num(self, inst_name):
        """
        return a device number which is not used
        """
        handler = self.get_handler()
        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        all_vbds = handler.xenapi.VM.get_VBDs(vm_ref)
        device_list = []
        for vbd_ref in all_vbds:
            device = handler.xenapi.VBD.get_userdevice(vbd_ref)
            device_list.append(int(device))
        max_num = max(device_list)
        for i in range(max_num + 1):
            if i not in device_list:
                return str(i)
        allowed_vbds = handler.xenapi.VM.get_allowed_VBD_devices(vm_ref)
        if str(max_num + 1) not in allowed_vbds:
            log.error("No avaiable VBD device to be allocated on VM [%s.]", inst_name)
            return ""

        return str(max_num + 1)

    def get_all_disk(self, inst_name):
        """
        return {'0': {'disk_size': 20.0, 'device_name': 'xvda'}, '3': {'disk_size': 0, 'device_name': 'xvdd'}}
        :param inst_name:
        :return: return a dict about all the virtual disk number, eg, 1,2, etc and its name in guest, eg:xvda, xvdd
        """
        handler = self.get_handler()

        vm_ref = self._get_vm_ref(inst_name)
        all_vdbs = handler.xenapi.VM.get_VBDs(vm_ref)
        device_dict = {}
        for vdb_ref in all_vdbs:
            device_number = handler.xenapi.VBD.get_userdevice(vdb_ref)
            device_name = handler.xenapi.VBD.get_device(vdb_ref)
            vdi_ref = handler.xenapi.VBD.get_VDI(vdb_ref)
            if "NULL" not in vdi_ref:
                disk_size = handler.xenapi.VDI.get_virtual_size(vdi_ref)
                disk_size = int(disk_size) / 1024.0 / 1024.0 / 1024.0
            else:
                disk_size = 0

            device_dict.setdefault(int(device_number), {'device_name': device_name, 'disk_size': disk_size})

        return device_dict

    def get_disk_size(self, inst_name, device_num):
        """
        :param inst_name: VM name
        :param device_num: the disk index number
        :return: return size in GB, or 0 if no device found
        """
        handler = self.get_handler()

        vm_ref = self._get_vm_ref(inst_name)
        all_vbds = handler.xenapi.VM.get_VBDs(vm_ref)
        for vbd_ref in all_vbds:
            if str(device_num) == handler.xenapi.VBD.get_userdevice(vbd_ref):
                break
        else:
            log.error("No virtual disk with device_num name [%s].", device_num)
            return 0

        vdi_ref = handler.xenapi.VBD.get_VDI(vbd_ref)
        if "NULL" not in vdi_ref:
            disk_size = handler.xenapi.VDI.get_virtual_size(vdi_ref)
            return int(disk_size) / 1024.0 / 1024.0 / 1024.0
        else:
            log.debug("No virtual disk with device_num [%s].", device_num)
            return 0

    def add_vdisk_to_vm(self, inst_name, storage_name='Local storage', size=2):
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
        except Exception as error:
            log.exception("No storage named [%s], exception: %s", storage_name, error)
            return False

        record["SR"] = sr_ref
        record["virtual_size"] = str(int(size) * 1024 * 1024 * 1024)  # size GB
        record['type'] = "user"
        record['read_only'] = False
        record['sharable'] = False
        record["other_config"] = {}
        try:
            vdi_ref = handler.xenapi.VDI.create(record)
        except Exception as error:
            log.error("Create VDI raise error:[%s]", error)
            return False

        vbd_record = {"VDI": vdi_ref, 'other_config': {}, 'mode': 'RW', 'type': 'Disk',
                      'empty': False, 'qos_algorithm_type': '', 'qos_algorithm_params': {}}
        vbd_record['userdevice'] = str(userdevice)
        vbd_record['bootable'] = False

        try:
            vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
            vbd_record['VM'] = vm_ref
            vbd_ref = handler.xenapi.VBD.create(vbd_record)
        except Exception as error:
            log.exception("Exception when create VBD: %s.", error)
            return False

        # only running VM support VBD plug
        if handler.xenapi.VM.get_power_state(vm_ref) != "Running":
            log.info("Virtual disk created, but didn't plugin.")
            return True

        try:
            log.info("Waiting for the virtual disk plug in...")
            sleep_time = 0
            while ((handler.xenapi.VBD.get_device(vbd_ref) == '') and (sleep_time < 10)):
                log.debug("wait device [%s] to plug in, sleep time %s.", handler.xenapi.VBD.get_device(vbd_ref),
                          sleep_time)
                time.sleep(2)
                handler.xenapi.VBD.plug(vbd_ref)
                sleep_time += 2
        except Exception as error:
            log.exception("Exception when plug VBD: %s", error)
            return False

        return True

    def __delete_virtual_disk_unused(self, storage_name, inst_name):
        """
        delete those VDI (virtual disk) which is not used by any VM; When delete a vm, the VDI is not deleted.
        :param storage_name:
        :param inst_name: the instance name to which virtual disk belongs. The VDI created by the api include the inst name
        :return:
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        try:
            sr_ref = self._hypervisor_handler.xenapi.SR.get_by_name_label(storage_name)[0]
            all_vdis = self._hypervisor_handler.xenapi.SR.get_VDIs(sr_ref)
            for vdi_ref in all_vdis:
                #  If there are VBDs attached with the VDI, don't delete; Deleted VM has no VBD attached to the VDI
                #  VDI.get_record(vdi), record['VBDs'], record['allowed_operations'], record['name_label']
                if self._hypervisor_handler.xenapi.VDI.get_VBDs(vdi_ref):
                    continue

                if not "destroy" in self._hypervisor_handler.xenapi.VDI.get_allowed_operations(vdi_ref):
                    continue
                #  Delete those vdi created by the api
                name_label = self._hypervisor_handler.xenapi.VDI.get_name_label(vdi_ref)
                if not str(name_label).startswith(inst_name):
                    continue

                try:
                    self._hypervisor_handler.xenapi.VDI.destroy(vdi_ref)
                except Exception:
                    log.warn("Destroy virtual disk [%s] failed.", vdi_ref)
        except Exception:
            log.exception("Except when delete VDI: %s", storage_name)
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
            # number of threads per core, xenserver6.5 has no infor about this, set default to 2
            ret_cpu_dict['thread_per_core'] = 2
            # number of cores per socket
            ret_cpu_dict['cores_per_socket'] = int(ret_cpu_dict['cpu_cores']) / int(ret_cpu_dict['cpu_sockets']) / int(
                    ret_cpu_dict['thread_per_core'])
        except Exception as error:
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
        except Exception as error:
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
        except  Exception as error:
            log.exception("No storage repository named: [%s], %s", storage_name, error)
            return ret_storage_dict

        total = self._hypervisor_handler.xenapi.SR.get_physical_size(sr_ref)
        used = self._hypervisor_handler.xenapi.SR.get_physical_utilisation(sr_ref)
        ret_storage_dict['size_total'] = float("%.3f" % (float(total) / 1024 / 1024 / 1024))
        ret_storage_dict['size_used'] = float("%.3f" % (float(used) / 1024 / 1024 / 1024))
        ret_storage_dict['size_free'] = float("%.3f" % (ret_storage_dict['size_total'] - ret_storage_dict['size_used']))
        return ret_storage_dict

    def get_host_mem_info(self):
        """
        Return HV memory info: Unit is GB
        """
        if self._hypervisor_handler is None:
            self._hypervisor_handler = self.get_handler()

        ret_mem_dict = {}
        try:
            host_ref = self._hypervisor_handler.xenapi.host.get_all()[0]
            host_metrics_ref = self._hypervisor_handler.xenapi.host.get_metrics(host_ref)
            total = self._hypervisor_handler.xenapi.host_metrics.get_memory_total(host_metrics_ref)
            free = self._hypervisor_handler.xenapi.host_metrics.get_memory_free(host_metrics_ref)
        except Exception as error:
            log.exception("Exception raised when get host memory infor:%s", error)
            return ret_mem_dict

        ret_mem_dict['size_total'] = float("%.3f" % (float(total) / 1024 / 1024 / 1024))
        ret_mem_dict['size_free'] = float("%.3f" % (float(free) / 1024 / 1024 / 1024))
        ret_mem_dict['size_used'] = float("%.3f" % (ret_mem_dict['size_total'] - ret_mem_dict['size_free']))
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
        except Exception as error:
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
        except Exception as error:
            log.error("Exception when get host platform infor:%s", error)

        return ret_plat_dict

    def get_host_name(self):
        """
        The name label of server.
        :return: (name_label, hostname)
        """
        handler = self.get_handler()
        host_ref = handler.xenapi.host.get_all()[0]
        name_label = handler.xenapi.host.get_name_label(host_ref)
        host_name = handler.xenapi.host.get_hostname(host_ref)

        return (name_label, host_name)

    def get_host_os(self, short_name=True):
        """
        :return: the host system information
        """
        handler = self.get_handler()
        system_info = {}
        try:
            host_ref = handler.xenapi.host.get_all()[0]
            record = handler.xenapi.host.get_software_version(host_ref)
            system_info['product_version'] = record.get('product_version', 'unknown')
            if short_name:
                return " ".join([record.get('product_brand', 'Unknown'), record.get('product_version', 'Unknown')])
            else:
                return record.get('xs:main', 'Unknown')
        except Exception as error:
            log.error("Exception when get host os infor:%s", error)

        return None


if __name__ == "__main__":
    from optparse import OptionParser


    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    (options, args) = parser.parse_args()
    virt = XenVirtDriver(hostname=options.host, user=options.user, passwd=options.passwd)
    # print virt.set_vm_static_memory(inst_name="test2", memory_max=1, memory_min=1)
    # print virt.set_vm_dynamic_memory("test2", 1, 1)
    # print virt.get_host_os()
    print virt.get_all_disk(inst_name="test_vm")
