#!/usr/bin/env python
#! -*- coding: utf-8 -*-
#########################################################################
# File Name: Xen/virt_driver_xen.py
# Attentions: provide command API for operations on Xenserver VMs, not using libvirtd
# Author: longhui
# Note: Please alternatively add params checking when use those API
# Created Time: 2018-02-08 11:34:12
#########################################################################

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

        return self._hypervisor_handler

    def delete_handler(self):
        '''
        release the session
        '''
        try:
            if self._hypervisor_handler is not None:
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
        '''
        if not self.is_instance_exists(inst_name):
            log.error("Instance with name %s doesn't exist.", inst_name)
            return False

        handler = self.get_handler()
        vm_ref = handler.xenapi.VM.get_by_name_label(inst_name)[0]
        record = handler.xenapi.VM.get_record(vm_ref)

        return record['power_state'] == 'Running'

    def create_instance(self, inst_name, reference_vm):
        '''
        @see: VM ref clone (session ref session_id, VM ref vm, string new_name)
        @see: void provision (session ref session_id, VM ref vm)
        '''
        handler = self.get_handler()
        try:
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
        if not self.is_instance_running(inst_name):
            log.info("VM [%s] is already not running.", inst_name)
            return True

        handler = self.get_handler()
        if handler is None:
            log.error("Can not get handler when try to power off VM [%s].", inst_name)
            return False
        try:
            handler.xenapi.VM.shutdown(inst_name)
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
            try:
                handler.xenapi.VM.start(vm_ref, False, False)
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
        except Exception, error:
            log.exception("Exception: %s when reboot VM [%s].", error, inst_name)
            return False

        return True

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


if __name__ == "__main__":
    log.info("test log")
    virt = XenVirtDriver("10.143.248.13", "root", "Mojiti!906")
    handler = virt.get_handler()
    vm_list = virt.get_vm_list()
    print vm_list
    for vm in vm_list:
        record = virt.get_vm_record(vm)
        if record:
            log.info("%s %s %s", vm, record['uuid'], record['name_label'])
