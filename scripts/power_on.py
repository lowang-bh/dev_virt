#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: power_on.py
 Author: longhui
 Created Time: 2018-03-02 11:14:26
'''

from optparse import OptionParser
import time
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory
from lib.Utils.db_utils import update_memory_to_database

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        power_on.py --all   [--host=ip --user=user --pwd=passwd]
        power_on.py vm1 vm2 [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("--all", dest="all", action="store_true",
                      help="Power on all VMs in server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""
    option_dic = {"host":options.host, "user":options.user, "passwd":options.passwd}


    if options.all:
        log.info("Start power on all VMs in server [%s].", host_name)
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        all_vms_names = virt_driver.get_vm_list()
        for vm_name in all_vms_names:
            log.info("Start power on VM [%s].", vm_name)
            virt_driver.power_on_vm(vm_name)
            time.sleep(0.5)
        for vm_name in all_vms_names:
            update_memory_to_database(vm_name, **option_dic)
        exit(0)
    elif args:
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        res_dict = {}
        for vm_name in args:
            if not virt_driver.is_instance_exists(vm_name):
                log.warn("No VM exists with name [%s].", vm_name)
                continue

            res_dict.setdefault(vm_name, 0)
            log.info("Start to power on VM [%s].", vm_name)
            ret = virt_driver.power_on_vm(vm_name)
            if not ret:
                log.error("VM [%s] power on failed.", vm_name)
                res_dict[vm_name] = 1
            time.sleep(0.5)
            update_memory_to_database(inst_name=vm_name, **option_dic)

        failed_vm_list = [item[0] for item in filter(lambda x:x[1] == 1, res_dict.items())]
        if failed_vm_list:
            log.fail("VMs %s power on failed.", str(failed_vm_list))
            exit(1)
        else:
            log.success("All VM power on successfully.")
            exit(0)
    else:
        parser.print_help()
        exit(0)

