#!/usr/bin/env python
#! -*- coding: utf-8 -*-
#########################################################################
# File Name: virt_factory.py
# Attentions: this file is used to generate relative production using diffent driver
# Author: longhui
# Created Time: 2018-02-08 11:29:36
#########################################################################

PLATFORM = "Xen"

if PLATFORM == "Xen":
    from lib.Val.Xen.virt_driver_xen import XenVirtDriver

if PLATFORM == "QEMU":
    from lib.Val.kvm.virt_driver_kvm import QemuVirtDriver


class VirtFactory(object):
    '''
    Virt Factory
    '''

    @classmethod
    def get_virt_driver(cls, host_name=None, user="root", passwd="passwd"):
        '''
        return virt driver
        '''
        if PLATFORM == 'Xen':
            return XenVirtDriver(host_name, user, passwd)

        if PLATFORM == 'QEMU':
            return QemuVirtDriver(host_name, user=user, passwd=passwd)

        raise TypeError('No virtual driver supported')

    @classmethod
    def get_vnet_driver(cls, host_name=None, user="root", passwd="passwd"):
        '''
        return vnet
        '''
        if PLATFORM == 'Xen':
            raise TypeError('No network driver supported for Xen platform')

        if PLATFORM == 'QEMU':
            raise TypeError('No network driver supported for Qemu platform')

        raise TypeError('No network driver supported')
