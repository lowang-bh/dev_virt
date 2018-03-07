#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: create_vm.py
 Author: longhui
 Created Time: 2018-03-01 13:20:26
'''
from optparse import OptionParser
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory, VM_MAC_PREFIX
from lib.Utils.vm_utils import is_IP_available, create_new_vif

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n

        create_vm.py -c new_vm_name -t template
        create_vm.py -c new_vm_name -t template [--host=ip --user=user --pwd=passwd]
        create_vm.py --list-vm       [--host=ip --user=user --pwd=passwd]
        create_vm.py --list-templ    [--host=ip --user=user --pwd=passwd]
        """
    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("-c", "--create", dest="vm_name",
                      help="Create a new VM with a template.")
    parser.add_option("-t", "--templ", dest="template",
                      help="Template used to create a new VM.")

    parser.add_option("--device", dest="device", help="The target device which vif attach(ed) to")
    parser.add_option("--ip", dest="vif_ip", help="The ip assigned to the virtual interface")
    parser.add_option("--netmask", dest="vif_netmask", help="The netmask for the target virtual interface")

    parser.add_option("--list-vm", dest="list_vm", action="store_true",
                      help="List all the vms in server.")
    parser.add_option("--list-templ", dest="list_templ", action="store_true",
                      help="List all the templates in the server.")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)

    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if options.list_vm:
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        all_vms = virt_driver.get_vm_list()
        if all_vms:
            log.info(str(all_vms))
        else:
            log.info("No VMs.")

    elif options.list_templ:
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        all_templs = virt_driver.get_templates_list()
        if all_templs:
            log.info(str(all_templs))
        else:
            log.info("No templates.")

    elif options.vm_name is not None:
        if options.template is None:
            log.fail("A template must be suppulied to create a new VM.")
            exit(1)
        new_vm_name, template_name = options.vm_name, options.template
        virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

        if virt_driver.is_instance_exists(new_vm_name):
            log.fail("There is already one VM named [%s]", new_vm_name)
            exit(1)
        if template_name not in virt_driver.get_templates_list():
            log.fail("No template named: %s", template_name)
            exit(1)
        if options.vif_ip is not None:
            option_dic = {"vif_ip":options.vif_ip, "vif_netmask":options.vif_netmask,
                          "device":options.device, "host":options.host,
                          "user":options.user, "passwd":options.passwd}
            if not is_IP_available(**option_dic):
                log.fail("IP check failed.")
                exit(1)
            mac_strs = ['%02x' % int(num) for num in options.vif_ip.split(".")]
            mac_addr = VM_MAC_PREFIX + ":%s:%s:%s:%s" % tuple(mac_strs)

        ret = virt_driver.create_instance(new_vm_name, template_name)
        if ret:
            log.success("Create VM [%s] successfully.", new_vm_name)
            exit(0)
        else:
            log.fail("Failed to create VM [%s].", new_vm_name)
            exit(1)
    else:
        parser.print_help()
        exit(1)

