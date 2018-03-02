#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: virt_driver_xen_test.py
 Author: longhui
 Created Time: 2018-03-01 13:46:58
'''
from lib.Val.Xen.virt_driver_xen import XenVirtDriver
virt_driver = XenVirtDriver()
assert virt_driver.is_instance_exists("new_vm") == True
assert virt_driver.delete_instance("new_vm") == True
assert virt_driver.is_instance_exists("new_vm") == False

