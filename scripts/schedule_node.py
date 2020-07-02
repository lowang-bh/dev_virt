#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: schedule_node.py
 Author: longhui
 Created Time: 2019-04-24 10:44:45
 Description: schedule different type of node to server, for k8s, jenkins, etcd cluster and so on 
"""
import json
import os
import pprint
from optparse import OptionParser

from lib.Log.log import log
from lib.Utils.constans import template_dict, DISK_POOL, DEFAULT_NETWORK, Libvirtd_User, Libvirtd_Pass
from lib.Utils.schedule import get_available_vm_info
from lib.Utils.vm_utils import VirtHostDomain


if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n
        schedule_node.py --role=rolename --cluster=[test|xyz|kvm]
        schedule_node.py --role=rolename --name=new_vm_name --host=hostip --ip=vm_ip
        schedule_node.py --list-roles
        """
    parser = OptionParser(usage=usage)
    parser.add_option("--role", dest="rolename", help="Config the target role of vm to create.")
    parser.add_option("--name", dest="new_vm_name", help="Config the target vm name.")
    parser.add_option("--host", dest="hostip", help="IP for the host server.")
    parser.add_option("--ip", dest="vm_ip", help="The ip assigned to the vm")
    parser.add_option("--cluster", dest="cluster", help="The target cluster name, support test|xyz|kvm")
    parser.add_option("--list-roles", dest="list_roles", action="store_true", help="List all supported role names")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if os.getenv("PLATFORM", "Xen") == "Xen":
        log.fail("This script does'n support 'Xen', please use create_vm.py instead.")
        exit(1)

    config_dict = template_dict
    try:
        config_file = os.path.join(os.path.dirname(__file__), "../etc/Nodeconfig.json")
        with open(config_file, "r") as f:
            try:
                config = json.load(f)
                config_dict.update(config)
            except (KeyError, ValueError) as e:
                log.fail("raised exception while load json: %s", e)
                exit(1)
    except IOError as err:
        log.warn("%s; Will use default config", err)

    log.debug(pprint.pformat(config_dict))

    if options.list_roles:
        log.info("Supported role names: %s", list(config_dict.keys()))
        log.info("You can add a role in the config file: %s", config_file)
        exit(0)

    # rolename is required.
    if options.rolename is None:
        log.fail("'--role=rolename' is required.")
        parser.print_help()
        exit(1)

    role_name = str.strip(options.rolename)
    if role_name not in config_dict:
        log.fail("Does not support role: %s", options.rolename)
        exit(1)

    # if "--cluster" is given, use  command "schedule_node.py --role=rolename --cluster=cluster-name" 
    if options.cluster is not None:
        cluster_name = options.cluster
        #  when no input, find default server and default vmname and IP
        host_name, new_vm_name, vm_ip = None, None, None
        host_name, new_vm_name, vm_ip = get_available_vm_info(role_name, cluster_name, config_dict)

        if host_name is None or vm_ip is None:
            log.fail("Can not scheduale new vm to a server, exiting...")
            exit(1)

        log.info(">>")
        log.info("Get schedualed VM with: host_ip=%s, new_vm_name=%s, vm_ip=%s", host_name, new_vm_name, vm_ip)
        log.info(">>")

        virthost = VirtHostDomain(host_name, Libvirtd_User, Libvirtd_Pass)
        if not virthost:
            log.fail("Can not connect to virtual driver or DB driver, initial VirtHostDomain failed.")
            exit(1)

    else:
        # use command "schedule_node.py --role=rolename  --name=new_vm_name --host=hostip --ip=vm_ip"
        if options.hostip is None or options.new_vm_name is None or options.vm_ip is None:
            log.fail("'--name=new_vm_name --host=hostip --ip=vm_ip' is required when with no '--cluster'.")
            exit(1)

        host_name = str.strip(options.hostip)
        new_vm_name = str.strip(options.new_vm_name)
        vm_ip = str.strip(options.vm_ip)

        virthost = VirtHostDomain(host_name, Libvirtd_User, Libvirtd_Pass)
        if not virthost:
            log.fail("Can not connect to virtual driver or DB driver, initial VirtHostDomain failed.")
            exit(1)

        # validate IP
        if not virthost.is_IP_available(vm_ip):
            log.fail("IP check failed.")
            exit(1)

    vnet_driver = virthost.vnet_driver
    virt_driver = virthost.virt_driver

    # create vm
    template_name = config_dict[role_name]["template"]
    if template_name not in virt_driver.get_templates_list():
        log.fail("No template named: %s", template_name)
        exit(1)
    ret = virthost.create_vm(new_vm_name, template_name)
    if not ret:
        log.fail("Failed to create VM [%s].Exiting....", new_vm_name)
        exit(1)

    log.info("New instance [%s] created successfully.", new_vm_name)

    # config cpu cores and memory
    memory, cpu_cores = config_dict[role_name]["memory"], config_dict[role_name]["cpu"]
    ret = virthost.config_vcpus(new_vm_name, vcpu_max=cpu_cores, vcpu_nums=cpu_cores)
    if not ret:
        log.warn("Config VCPU cores failed, keep same as before...")

    log.debug("memory_size:%s, min_memory:%s, max_memory:%s", memory, memory, memory)
    ret = virthost.config_max_memory(new_vm_name, static_max=memory)
    if not ret:
        log.warn("Configure max memory size failed, keep same as before...")
    ret = virthost.config_min_memory(new_vm_name, static_min=memory)
    if not ret:
        log.warn("Config min memory size failed, keep same as before...")
    ret = virthost.config_memory(new_vm_name, dynamic_min=memory, dynamic_max=memory)
    if not ret:
        log.warn("Config target memory size failed, keep same as before...")

    # config IP
    ret = virthost.config_vif(new_vm_name, "0", network=DEFAULT_NETWORK, ip=vm_ip)
    if not ret:
        log.warn("Vif configure failed.")
    else:
        log.info("Successfully configured the virtual interface device [0] to VM [%s].", new_vm_name)

    # add disk
    if "add_disk_num" in config_dict[role_name]:
        add_disk_num = config_dict[role_name]["add_disk_num"]
        disk_size = config_dict[role_name]["disk_size"]
        while add_disk_num > 0:
            add_disk_num -= 1
            ret = virthost.add_vm_disk(new_vm_name, storage_name=DISK_POOL, size=disk_size)
            if ret:
                log.info("Successfully add a new disk with size [%s]GB to VM [%s].", disk_size, new_vm_name)
            else:
                log.warn("Failed to add a new disk with size [%s]GB to VM [%s].", disk_size, new_vm_name)

    # power on vm
    ret = virthost.power_on_vm(new_vm_name)
    if ret:
        log.success("Create VM [%s] and power on successfully.", new_vm_name)
        exit(0)
    else:
        log.fail("VM [%s] created, but power on failed.", new_vm_name)
        exit(1)
