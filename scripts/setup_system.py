#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: setup_system.py
 Author: longhui
 Created Time: 2018-05-17 13:11:04
 This script is used to create multiple VMS in multiple xenservers by parse the given xml
"""

import os
import time
from optparse import OptionParser
from lib.Log.log import log
import lib.Utils.xml_utils as xml_utils
from lib.Utils.vm_utils import VirtHostDomain


if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n
        setup_system.py --validate xmlFile
        setup_system.py --create   xmlFile
        """
    parser = OptionParser(usage=usage)
    parser.add_option("--validate", dest="validate", action="store_true", help="Validate the given xml file")
    parser.add_option("--create", dest="create", action="store_true", help="Do the create up according to the xml file")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    create, validate = False, False
    if options.validate:
        validate = True
    elif options.create:
        validate, create = True, True
    else:
        parser.print_help()
        exit(1)
    if len(args) != 1:
        parser.print_help()
        exit(1)

    filename = args[0]
    if not os.path.isfile(filename):
        log.fail("Can not find xml file: %s, please check it.", filename)
        exit(1)
    schema_filepath = os.path.dirname(__file__)
    if not xml_utils.validate(os.path.join(schema_filepath, "../etc/schema.xsd"), filename):
        log.fail("XML file '%s' did not validate with the schema.xsd!", filename)
        exit(1)

    # start to create via xml
    parsed_xml = xml_utils.parse_xml(filename)
    #[{'passwd': '123456', 'host': '192.168.1.10', 'user': 'root', 'vms': []}]

    # 1. validate xml items
    for server in parsed_xml:
        hostname, user, passwd = server['host'], server['user'], server['passwd']
        log.info("Start to validate VMs in server: %s", hostname)
        virthost = VirtHostDomain(hostname, user, passwd)
        if not virthost:
            log.fail("Can not connect to host [%s] or DB driver, initial VirtHostDomain failed.", hostname)
            exit(1)

        vnet_driver = virthost.vnet_driver
        virt_driver = virthost.virt_driver
        # {'cpucores': '2', 'vmname': 'createViaXml', 'maxMemory': '4', 'disks': [{'storage': 'Local storage', 'size': '2'}],
        #  'ips': [{'vifIndex': '0', 'netmask': None, 'network': 'xenbr1', 'ip': '192.168.1.240'}],
        #  'cpumax': '4', 'memory': '2', 'minMemory': None}
        default_sr = virthost.get_max_free_size_storage()
        all_sr_info = virthost.get_host_all_storage_info()
        free_memory = virt_driver.get_host_mem_info()['size_free']
        total_memory = 0
        disk_size = {}
        iplist = []
        device_list = virthost.get_all_devices()
        bridge_list = virthost.get_bridge_list()
        network_list = virthost.get_network_list()
        for vm in server['vms']:
            if virt_driver.is_instance_exists(vm['vmname']):
                log.fail("There is already one VM named [%s]", vm['vmname'])
                exit(1)
            if vm['template'] not in virt_driver.get_templates_list():
                log.fail("No template named: %s on server %s", vm['template'], virthost.server_name)
                exit(1)
            if vm['memory']:
                total_memory += float(vm['memory'])
            if vm['minMemory'] and  vm['memory'] and vm['minMemory'] > vm['memory']:
                log.fail("minMemory should not be more than memory!")
                exit(1)
            if vm['maxMemory'] and  vm['memory'] and vm['maxMemory'] < vm['memory']:
                log.fail("maxMemory should  be more than memory!")
                exit(1)
            for diskdic in vm['disks']:
                storage = diskdic['storage']
                if not storage:
                    storage = default_sr
                elif storage not in all_sr_info:
                    log.fail("No storage named '%s' in server %s.", storage, virthost.server_name)
                    exit(1)
                disk_size.setdefault(storage, 0)
                disk_size[storage] += float(diskdic['size'])
            #IP validation
            vif_index_list = []
            for ipdic in vm['ips']:
                if ipdic['ip'] not in iplist:
                    iplist.append(ipdic['ip'])
                else:
                    log.fail('Duplicate ip:[%s] in vm [%s].', ipdic['ip'], vm['vmname'])
                    exit(1)
                if ipdic['vifIndex'] not in vif_index_list:
                    vif_index_list.append(ipdic['vifIndex'])
                else:
                    log.fail("Duplicate vif index:[%s] in vm [%s].", ipdic['vifIndex'], vm['vmname'])
                    exit(1)
                if ipdic['device'] and ipdic['device'] not in device_list:
                    log.fail("No available device [%s] in server [%s].", ipdic['device'], hostname)
                    exit(1)
                if ipdic['network'] and ipdic['network'] not in network_list:
                    log.fail("No available network [%s] in server [%s].", ipdic['network'], hostname)
                    exit(1)
                if ipdic['bridge'] and ipdic['bridge'] not in bridge_list:
                    log.fail("No available bridge [%s] in server [%s].", ipdic['bridge'], hostname)
                    exit(1)
                log.debug("VM [%s] has a IP infor: %s", vm['vmname'], ipdic)
                if not virthost.is_IP_available(ipdic['ip'], ipdic['netmask'], ipdic['device'], ipdic['network'], ipdic['bridge']):
                    log.fail("IP [%s] check failed in vm [%s].", ipdic['ip'], vm['vmname'])
                    exit(1)

        if total_memory > free_memory:
            log.error("Total memory %s exceed the limit of free memory %s in server %s", total_memory, free_memory, virthost.server_name)
            log.fail("Validate memory failed in xml file %s.", filename)
            exit(1)

        for storage_key, storage_value in disk_size.iteritems():
            if storage_value >  all_sr_info[storage_key][1] -1: #
                log.error("There is only %sGB in storage: %s, but all VMs disk need: %sGB on '%s'.", all_sr_info[storage_key][1], storage_key, storage_value, storage_key)
                log.fail("Disk validate failed in xml: %s", filename)
                exit(1)

    if not create:
        log.success("All resource validate successfully.")
        exit(0)
    else:
        log.info("All resource validate successfully.")
    # 2. create vms in xml
    for server in parsed_xml:
        hostname, user, passwd = server['host'], server['user'], server['passwd']
        virthost = VirtHostDomain(hostname, user, passwd)
        vnet_driver = virthost.vnet_driver
        virt_driver = virthost.virt_driver

        log.info("Start to create VMs in server: %s", hostname)
        for vm in server['vms']:
            vmname = vm['vmname']
            log.info("Start to create vm [%s]!", vmname)
            ret = virthost.create_vm(vmname, vm['template'])
            if not ret:
                log.fail("Failed to create VM [%s].Exiting....", vmname)
                exit(1)
            log.info("New instance [%s] created successfully.", vmname)

            log.info("Start to config vm [%s].", vmname)

            virthost.config_vcpus(vmname, vcpu_max=vm['cpumax'])
            if vm['maxMemory']:
                virthost.config_max_memory(vmname, static_max=vm['maxMemory'])
            if vm['minMemory']:
                virthost.config_min_memory(vmname, static_min=vm['minMemory'])
            if vm['memory']:
                virthost.config_memory(vmname, dynamic_min=vm['memory'], dynamic_max=vm['memory'])

            for ipdic in vm['ips']:
                virthost.config_vif(vmname, ipdic['vifIndex'], ipdic['device'], ipdic['network'], ipdic['bridge'], ipdic['ip'])

            for diskdic in vm['disks']:
                storage = diskdic['storage']
                if not storage:
                    storage = virthost.get_max_free_size_storage() # calc the default sr online
                virthost.add_vm_disk(vmname, storage, diskdic['size'])

            ret = virthost.power_on_vm(vmname)
            if not ret:
                log.warn("Create VM [%s] successfully, but power on vm return False.", vmname)
            else:
                if vm['cpucores']:
                    t =0
                    while t <= 10 and not virthost.allowed_set_vcpu_live(vmname):
                        log.info("Waiting vm to power on and set vcpu lively....")
                        time.sleep(2)
                        t += 2
                    if virthost.allowed_set_vcpu_live(vmname):
                        virthost.config_vcpus(vmname, vcpu_nums=vm['cpucores'])
                    else:
                        log.warn("After waiting for %ss and haven't power on to set vcpu lively.", t)
                log.info("Create VM [%s] and power on successfully", vmname)

    log.success("All vms created on all servers.")
    exit(0)




