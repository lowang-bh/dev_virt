#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: virt_driver_xen_test.py
 Author: longhui
 Created Time: 2018-03-01 13:46:58
'''
import unittest
import time
from lib.Val.Xen.virt_driver_xen import XenVirtDriver


class XenVirtDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.virt_driver = XenVirtDriver(hostname="192.168.1.2", user="root", passwd="123456")
        self.vms = ['t2-dev16', 't2-jenkins-lain2', 't2-dev24', 't2-dev23', 't2-dev25', 't2-dev26', 't2-dev22']

    def tearDown(self):
        self.virt_driver.delete_handler()

    def test_get_handler(self):
        self.handler = self.virt_driver.get_handler()
        self.assertIsNotNone(self.handler, "handler is None")

    def test_get_vm_list(self):
        dst_vms = self.virt_driver.get_vm_list()
        for vm in self.vms:
            self.assertEqual(vm in dst_vms, True, "%s not there" % vm)

    def test_get_template_list(self):
        templates = ["CentOS 7.2 for Lain"]
        dst_templates = self.virt_driver.get_templates_list()
        self.assertNotEqual(dst_templates, [], "get_templates_list() return []")
        for templ in templates:
            self.assertEqual(templ in dst_templates, True, "%s not there" % templ)

    def test_is_instance_running(self):
        for vm in self.vms:
            self.assertEqual(self.virt_driver.is_instance_running(vm), True, "%s is not running" % vm)

#    def test_power_on_vm(self):
#        vm = "new_vm"
#        self.assertEqual(self.virt_driver.is_instance_running(vm), False, "%s is already running" % vm)
#        self.assertTrue(self.virt_driver.power_on_vm(vm), "%s power on failed" % vm)
#        time.sleep(0.5)
#        self.assertTrue(self.virt_driver.is_instance_running(vm), "%s should be in running" % vm)

    def test_power_off_vm(self):
        vm = "new_vm"
        self.assertTrue(self.virt_driver.power_off_vm(vm), "%s power off failed" % vm)
        time.sleep(0.5)
        self.assertFalse(self.virt_driver.is_instance_running(vm), "%s should not be in running" % vm)


if __name__ == "__main__":
    unittest.main()

