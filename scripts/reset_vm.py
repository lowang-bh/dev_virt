#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: reset_vm.py
 Author: longhui
 Created Time: 2018-03-01 11:14:57
'''

from optparse import OptionParser
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("--all", dest="all", action="store_true",
                      help="Reset all VMs in this server")
    parser.add_option("--vm", dest="vm",
                      help="Reset VM in this server")

    (options, args) = parser.parse_args()

    if options.all:
        log.info("Start reset all VMs in server.")
        virt_driver = VirtFactory.get_virt_driver()
        all_vms_names = virt_driver.get_vm_list()
        for vm_name in all_vms_names:
            log.info("Start reset VM [%s].", vm_name)
            virt_driver.reboot(vm_name)
        exit(0)

    elif options.vm is not None:
        vm_name = options.vm
        virt_driver = VirtFactory.get_virt_driver()
        if not virt_driver.is_instance_exists(vm_name):
            log.fail("No VM named %s.", vm_name)
            exit(1)

        ret = virt_driver.reboot(vm_name)
        if ret:
            log.success("VM [%s] reset successfully.", vm_name)
            exit(0)
        else:
            log.fail("VM [%s] reset failed.", vm_name)
            exit(1)
    else:
        parser.print_help()
        exit(0)

