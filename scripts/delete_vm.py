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
from lib.Utils.signal_utils import timeout_func
from lib.Utils.vm_utils import VirtHostDomain

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        delete_vm.py  --vm=vm_name [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    parser.add_option("--vm", dest="vm", help="Delete an unused VM in server, the disk will not be deleted")

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

    if options.vm:
        vm_name = options.vm
        if not virt_driver.is_instance_exists(vm_name):
            log.fail("No VM named %s.", vm_name)
            exit(1)
        #  need user to confirm the input
        # answer = input("Are you sure to delete those VMs: %s ?(Yes/No)" % args)
        prompt = "Are you sure to delete those VMs: %s? (Yes/No)\n" % args
        answer = timeout_func(raw_input, 5, None, prompt)
        if answer != "Yes":
            log.info("Your input is not 'Yes'. Exiting...")
            exit(0)
        else:
            log.info("You input 'Yes' to confirm the deletion.")

        ret = virthost.delete_vm(vm_name)
        if not ret:
            log.fail("VM [%s] deleted failed.", vm_name)
            exit(1)
        else:
            log.success("VM [%s] has been deleted successfully.", vm_name)
            exit(0)

    else:
        parser.print_help()
        exit(0)
