#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: create_vm.py
 Author: longhui
 Created Time: 2018-03-01 13:20:26
'''
from optparse import OptionParser
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        create_vm.py -c new_vm_name -f template_name
        create_vm.py -c new_vm_name -f template [--host=ip --user=user --pwd=passwd]
        """
    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("-c", "--create", dest="vm_name",
                      help="Create a new VM with a template.")
    parser.add_option("-t", "--templ", dest="template",
                      help="Template used to create a new VM.")
    parser.add_option("--ip", dest="ip",
                      help="IP for new VM.")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))
    if options.vm_name is None:
        parser.print_help()
        exit(1)

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)

    if options.vm_name is not None and options.template is None:
        log.fail("A template must be suppulied to create a new VM.")
        exit(1)

    new_vm_name, template_name = options.vm_name, options.template
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    if virt_driver.is_instance_exists(new_vm_name):
        log.fail("There is already one VM named [%s]", new_vm_name)
        exit(1)
    if template_name not in virt_driver.get_templates_list():
        log.fail("No template named: %s", template_name)
        exit(1)

    ret = virt_driver.create_instance(new_vm_name, template_name)
    if ret:
        log.success("Create VM [%s] successfully.", new_vm_name)
        exit(0)
    else:
        log.fail("Failed to create VM [%s].", new_vm_name)
        exit(1)

