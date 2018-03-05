#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: delete_vm.py
 Author: longhui
 Created Time: 2018-03-01 13:20:47
'''

from optparse import OptionParser
import time
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        delete_vm.py vm1 vm2 [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if args:
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        res_dict = {}
        for vm_name in args:
            if not virt_driver.is_instance_exists(vm_name):
                log.error("No VM exists with name [%s].", vm_name)
                continue

            res_dict.setdefault(vm_name, 0)
            log.info("Start to delete VM [%s].", vm_name)
            ret = virt_driver.delete_instance(vm_name)
            if not ret:
                log.error("VM [%s] deleted failed.", vm_name)
                res_dict[vm_name] = 1
            time.sleep(0.5)

        failed_vm_list = [item[0] for item in filter(lambda x:x[1] == 1, res_dict.items())]
        if failed_vm_list:
            log.fail("VMs %s deleted failed.", str(failed_vm_list))
            exit(1)
        else:
            log.success("All VMs have been deleted successfully.")

    else:
        parser.print_help()
        exit(0)
