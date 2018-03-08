#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: reset_vm.py
 Author: longhui
 Created Time: 2018-03-01 11:14:57
'''

from optparse import OptionParser
import time
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        reset_vm.py --all       [--host=ip --user=user --pwd=passwd]
        reset_vm.py --vm=vmname [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("--all", dest="all", action="store_true",
                      help="Reset all VMs in this server")
    parser.add_option("--vm", dest="vm",
                      help="Reset VM in server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if options.all:
        log.info("Start reset all VMs in server.")
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        all_vms_names = virt_driver.get_vm_list()
        for vm_name in all_vms_names:
            log.info("Start reset VM [%s].", vm_name)
            time.sleep(1)
            virt_driver.reboot(vm_name)
        exit(0)

    elif options.vm is not None:
        vm_name = options.vm
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        if not virt_driver.is_instance_exists(vm_name):
            log.fail("No VM named %s.", vm_name)
            exit(1)

        log.info("Start to reset [%s]", vm_name)
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

