#!/usr/bin/env python
#! -*- coding: utf-8 -*-
#########################################################################
# File Name: Xen/virt_driver_xen.py
# Attentions: provide command API for operations on Xenserver VMs, not using libvirtd
# Author: longhui
# Created Time: 2018-02-08 11:34:12
#########################################################################

from lib.Log.log import log
from lib.Val.virt_driver import VirtDriver
import XenAPI

API_VERSION_1_1 = '1.1'


class XenVirtDriver(VirtDriver):
    '''
    '''

    def __init__(self, hostname=None, user=None, passwd=None):
        VirtDriver.__init__(self, hostname, user, passwd)
        self._hypervisor_handler = None

        if self.hostname is None:
            self.hostname = 'localhost'

        self._hypervisor_handler = self.get_handler()

    def __del__(self):
        if self._hypervisor_handler is not None:
            self._hypervisor_handler.xenapi.session.logout()
            self._hypervisor_handler = None

    def get_handler(self):
        '''
        return the handler of the virt_driver
        '''
        if self._hypervisor_handler is not None:
            return self._hypervisor_handler

        self._hypervisor_handler = XenAPI.xapi_local()  #no __nonzero__, can not use if/not for bool test
        try:
            self._hypervisor_handler.xenapi.login_with_password(self.user, self.passwd, API_VERSION_1_1, 'XenVirtDriver')
        except Exception, error:
            log.error(error)
            return None

        return self._hypervisor_handler

    def delete_handler(self):
        '''
        release the session
        '''
        if self._hypervisor_handler:
            self._hypervisor_handler.xenapi.session.logout()
            self._hypervisor_handler = None

    def get_vm_list(self):
        """
        Return the VMs from system
        """
        handler = self.get_handler()

    def is_instance_exists(self, inst_name):
        '''
        @note Object name_label fields are not guaranteed to be unique and so the get_by_name_label
        API call returns a set of references rather than a single reference.
        '''

