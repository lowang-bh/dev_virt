#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################################
# File Name: virt_factory.py
# Attentions: this file is used to generate relative production using diffent driver
# Author: longhui
# Created Time: 2018-02-08 11:29:36
#########################################################################

import os
PLATFORM = os.getenv("PLATFORM", "Xen")

if PLATFORM == "Xen":
    VM_MAC_PREFIX = "00:66"
    from lib.Val.Xen.virt_driver_xen import XenVirtDriver
    from lib.Val.Xen.vnet_driver_xen import XenVnetDriver

if PLATFORM == "KVM":
    from lib.Val.kvm.virt_driver_kvm import QemuVirtDriver
    from lib.Val.kvm.vnet_driver_kvm import QemuVnetDriver
    VM_MAC_PREFIX = "52:54"


class VirtFactory(object):
    '''
    Virt Factory
    '''

    @classmethod
    def get_virt_driver(cls, host_name=None, user="root", passwd=""):
        '''
        return virt driver
        '''
        if PLATFORM == 'Xen':
            return XenVirtDriver(host_name, user, passwd)

        if PLATFORM == 'KVM':
            return QemuVirtDriver(host_name, user=user, passwd=passwd)

        raise TypeError('No virtual driver supported')

    @classmethod
    def get_vnet_driver(cls, host_name=None, user="root", passwd="passwd"):
        '''
        return vnet
        '''
        if PLATFORM == 'Xen':
            return XenVnetDriver(host_name, user, passwd)

        if PLATFORM == 'KVM':
            return  QemuVnetDriver(host_name, user, passwd)

        raise TypeError('No network driver supported')
