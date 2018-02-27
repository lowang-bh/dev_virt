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
TARGET_HV = "qemu:///session"

HV_EXE_SUCCESS = 0
HV_EXE_ERROR = -1

# the vm's disk should be in VM_HOUSE
VM_HOUSE = "/datastore/"

# the xml file pool, which contains all the xml templates
#TEMPLATE_CFG_POOL = "/etc/libvirt/qemu/"  # default path


class QemuVirtDriver(VirtDriver):
    '''
    derived class of VirtDriver
    '''

    def __init__(self, host_name=None, user=None, passwd=None):
        VirtDriver.__init__(self, host_name, user, passwd)
        self._hypervisor_handler = None

        if self.host_name is None:
            self.host_name = "localhost"
        self._auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], self._request_cred, None]

        log.debug("Try to connect to libvirt in host: %s", self.host_name)
        # conn = libvirt.open(name) need root username
        # conn = libvirt.openReadOnly(name) has not write promission
        # self._hypervisor_root_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.host_name, '/system'), self._auth, 0)

        self._hypervisor_root_handler = None
        self._hypervisor_handler = libvirt.open(TARGET_HV)

    def _request_cred(self, credentials, user_data):
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = self.user
            elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                credential[4] = self.passwd
        return 0

    def __del__(self):

        if self._hypervisor_handler:
            log.debug("try to close the connect to libvirt: %s", self.host_name)
            self._hypervisor_handler.close()

    def _get_root_handler(self):
        """
        Return the root handler of libvirt
        """
        if self._hypervisor_root_handler:
            return self._hypervisor_root_handler

        self._hypervisor_root_handler = libvirt.openAuth("{0}{1}{2}".format('qemu+tcp://', self.host_name, '/system'), self._auth, 0)
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

        self._hypervisor_handler = libvirt.open(TARGET_HV)
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
