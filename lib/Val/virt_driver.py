#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Pw @ 2018-02-07 11:15:48

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class VirtDriver(object):
    '''
    abstract class for virt driver
    '''

    def __init__(self, hostname=None, user=None, passwd=None):
        self.hostname = hostname
        self.user = user
        self.passwd = passwd
        self._hypervisor_handler = None

    def __nonzero__(self):
        if self._hypervisor_handler is None:
            return False
        return True

    @staticmethod
    def timeout_handler(signal_num, frame):
        """
        :param signal_num:
        :param frame:
        :return:
        """
        raise Exception("get timeout signal.")

    @abc.abstractmethod
    def get_vm_list(self):
        """
        :description get all the instances names on host
        :return a list of VM names
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_templates_list(self):
        """
        :description get all the templates on host
        :return a list of tempaltes names
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def is_instance_exists(self, inst_name):
        '''
        :description check whether the instance exists in virt-platform
        :param inst_name: the instance name
        :return True or False
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def is_instance_running(self, inst_name):
        '''
        @param inst_name: instance name
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def is_instance_halted(self, inst_name):
        '''
        @param inst_name: instance name
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def create_instance(self, inst_name, reference_vm, storage_pool=None):
        '''
        @param inst_name: new instance name
        @param reference_vm: template name
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_instance(self, inst_name, delete_disk=False):
        '''
        :param inst_name, instance name
        :param delete_disk, remove disk or not
        :return True or False based on whether it is successful
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def power_off_vm(self, inst_name):
        '''
        :param inst_name, instance name
        :return True or False
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def power_on_vm(self, inst_name):
        '''
        :param inst_name, power on vm
        :return True or False
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def reboot(self, inst_name):
        '''
        @param inst_name: instance name
        @return: True or False based on whether it is successful
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def add_vdisk_to_vm(self, inst_name, storage_name, size):
        """
        @param inst_name: the name of VM
        @param storage_name: which storage repository the virtual disk put
        @param size: the disk size
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_cpu_info(self):
        """
        Return HV CPU info with dict: cpu speed: MHZ; cpu_sockets,cpu_cores, cpu_model
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_storage_info(self, storage_name):
        """
        Return HV storage info: Unit is GB
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_mem_info(self):
        """
        Return HV memory info: Unit is MB
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_sw_ver(self, short_name=True):
        """
        Return the HV SW version
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_plat_info(self):
        """
        Return HV platform info
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vm_record(self, inst_name):
        """
        return the record dict for inst_name
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_all_storages(self):
        """
        return a list of all the storage names
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_disk_size(self, inst_name, device_num):
        """
        :param inst_name: VM name
        :param device_num: the disk index number
        :return: return size in GB, or 0 if no device found
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_disk(self, inst_name):
        """
        :param inst_name:
        :return: return all the virtual disk number, eg, 1,2, etc and its name in guest, eg:hda1
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_os_type(self, inst_name):
        '''
        get the os type, return string
        '''
        raise NotImplementedError()

    @abc.abstractmethod
    def set_vm_vcpu_live(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a running VM
        :param inst_name:
        :param vcpu_num: should be str of a int number
        :return: True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_vm_vcpu_max(self, inst_name, vcpu_num):
        """
        set the vcpu numbers for a halted VM
        :param inst_name:
        :param vcpu_num:
        :return: True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vm_vcpu_current(self, inst_name):
        """
        :return: the current vcpu number or 0
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_vm_vcpu_max(self, inst_name):
        """
        :param inst_name:
        :return: max cpu number or 0
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_name(self):
        """
        The name label of server.
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_vm_static_memory(self, inst_name, memory_max, memory_min):
        """
        :param inst_name:
        :param memory_max: size of GB
        :param memory_min: size of GB
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_vm_dynamic_memory(self, inst_name, memory_max, memory_min):
        """
        :param inst_name:
        :param max_memory:
        :param min_memory:
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_vm_memory_live(self, inst_name, memory_target):
        """
        :param memory_target: Memory in GB
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_host_os(self, short_name=True):
        """
        :return: the host system information
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def allowed_set_vcpu_live(self, inst_name):
        """
        :param inst_name:
        :return: True if allowed to set vcpu lively, else False
        """
        raise NotImplementedError()
