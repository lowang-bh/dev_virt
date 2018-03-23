#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: dump_vm.py
 Author: longhui
 Created Time: 2018-03-18 21:59:34
'''

from optparse import OptionParser
from lib.Log.log import log
from lib.Utils.vm_utils import print_vm_info, print_vm_disk_info, print_all_vifs_info
from lib.Val.virt_factory import VirtFactory

if __name__ == "__main__":
    usage = """usage: %prog [options] vm_name\n
        dump_vm.py  vm_name  [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    parser.add_option("--list", dest="list", action="store_true", help="List the cpu and memory information")
    parser.add_option("--list-disk", dest="list_disk", action="store_true", help="List the virtual disk size")
    parser.add_option("--list-vifs", dest="list_vifs", action="store_true", help="List all the VIFs information")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if not args:
        log.fail("Please specify a VM name to config.")
        parser.print_help()
        exit(1)

    vm_name = args[0]
    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    if not virt_driver.is_instance_exists(vm_name):
        log.fail("No VM named [%s].", vm_name)
        exit(1)

    option_dic = {"host":options.host, "user":options.user, "passwd":options.passwd}

    if options.list:
        print_vm_info(vm_name, **option_dic)
    elif options.list_disk:
        print_vm_disk_info(inst_name=vm_name, **option_dic)
    elif options.list_vifs:
        print_all_vifs_info(inst_name=vm_name, **option_dic)
    else:
        print_vm_info(vm_name, **option_dic)
        print_vm_disk_info(inst_name=vm_name, **option_dic)
        print_all_vifs_info(inst_name=vm_name, **option_dic)

    exit(0)
