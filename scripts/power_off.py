#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: power_off.py
 Author: longhui
 Created Time: 2018-03-02 11:14:36
'''

from optparse import OptionParser
import time
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory
from lib.Utils.vm_utils import VirtHostDomain

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        power_off.py --all   [--host=ip --user=user --pwd=passwd]
        power_off.py vm1 vm2 [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("--all", dest="all", action="store_true",
                      help="Power off all VMs in server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    virthost = VirtHostDomain(host_name, user, passwd)
    if not virthost:
        log.fail("Can not connect to virtual driver or DB driver, initial VirtHostDomain failed.")
        exit(1)

    virt_driver = virthost.virt_driver

    if options.all:
        log.info("Start power off all VMs in server [%s].", host_name)
        all_vms_names = virt_driver.get_vm_list()
        for vm_name in all_vms_names:
            virthost.power_off_vm(vm_name)
            time.sleep(0.5)
        exit(0)

    elif args:
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        res_dict = {}
        for vm_name in args:
            if not virt_driver.is_instance_exists(vm_name):
                log.warn("No VM exists with name [%s].", vm_name)
                continue

            res_dict.setdefault(vm_name, 0)
            ret = virthost.power_off_vm(vm_name)
            if not ret:
                log.error("VM [%s] power on failed.", vm_name)
                res_dict[vm_name] = 1
            time.sleep(0.5)

        failed_vm_list = [item[0] for item in filter(lambda x:x[1] == 1, res_dict.items())]
        if failed_vm_list:
            log.fail("VMs %s power on failed.", str(failed_vm_list))
            exit(1)
        else:
            log.success("All VMs in %s power off successfully.", args)
    else:
        parser.print_help()
        exit(0)
