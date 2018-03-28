#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: scripts/config_vm.py
 Author: longhui
 Created Time: 2018-03-07 09:38:18
'''

from optparse import OptionParser
from lib.Log.log import log
from lib.Utils.vm_utils import VirtHostDomain

if __name__ == "__main__":
    usage = """usage: %prog [options] vm_name\n
        config_vm.py vm_name --add-vif=vif_index --device=eth0  [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --del-vif=vif_index   [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --vif=vif_index --device=eth0 --ip=ip [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --add-disk=size --storage=storage_name    [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --cpu-core=num | --cpu-max=max      [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --list-vif            [--host=ip --user=user --pwd=passwd]
        config_vm.py         --list-pif            [--host=ip --user=user --pwd=passwd]
        config_vm.py         --list-SR             [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Password for host server")

    parser.add_option("--add-vif", dest="add_index", help="Add a virtual interface device to guest VM")
    parser.add_option("--del-vif", dest="del_index", help="Delete a virtual interface device from guest VM")
    parser.add_option("--vif", dest="vif_index", help="Configure on a virtual interface device")

    parser.add_option("--device", dest="device", help="The target physic NIC name with an associated network vif attach(ed) to")
    parser.add_option("--network", dest="network", help="The target bridge/switch network which vif connect(ed) to")
    parser.add_option("--ip", dest="vif_ip", help="The ip assigned to the virtual interface")
    parser.add_option("--netmask", dest="vif_netmask", help="The netmask for the target virtual interface")

    parser.add_option("--add-disk", dest="disk_size", help="The disk size(GB) add to the VM")
    parser.add_option("--storage", dest="storage_name", help="The storage location where the virtual disk put")

    parser.add_option("--cpu-cores", dest="cpu_cores", help="Config the VCPU cores lively")
    parser.add_option("--cpu-max", dest="max_cores", help="Config the max VCPU cores.")
    parser.add_option("--memory", dest="memory_size", help="Config the memory size in GB.")

    parser.add_option("--list-vif", dest="list_vif", action="store_true",
                      help="List the virtual interface device in guest VM")
    parser.add_option("--list-pif", dest="list_pif", action="store_true",
                      help="List the interface device in the host")
    parser.add_option("--list-SR", dest="list_sr", action="store_true",
                      help="List the storage repository infor in the host")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if not options.list_vif and not options.list_pif and not options.list_sr and\
        (not options.vif_index and not options.del_index and not options.add_index and
         not options.disk_size and not options.cpu_cores and not options.max_cores and
        not options.memory_size):
        parser.print_help()
        exit(1)

    virthost = VirtHostDomain(host_name, user, passwd)
    if not virthost:
        log.fail("Can not connect to virtual driver, initial VirtHostDomain failed.")
        exit(1)

    vnet_driver = virthost.vnet_driver
    virt_driver = virthost.virt_driver

    if options.list_pif:
        pif_list = vnet_driver.get_all_devices()
        if pif_list:
            log.info("All device on the host: %s", sorted(pif_list))
        else:
            log.info("No device found on the host.")
        exit(0)

    if options.list_sr:
        sr_name_list = virt_driver.get_host_all_storages()
        log.info("All SR information:")
        infor_formate = "%-20s\t%s"
        log.info(infor_formate, "Storage_name", "Free_size(GB)")
        for sr_name in sr_name_list:
            storage = virt_driver.get_host_storage_info(storage_name=sr_name)
            log.info(infor_formate, sr_name, storage["size_free"])
        exit(0)

    if not args:
        log.error("Please specify a VM name to config.")
        parser.print_help()
        exit(1)

    inst_name = args[0]
    if not virt_driver.is_instance_exists(inst_name):
        log.fail("No instance exist with name [%s].", inst_name)
        exit(1)

    if options.list_vif:
        vif_list = vnet_driver.get_all_vifs_indexes(inst_name)
        if vif_list:
            log.info("All virtual interface device: %s", sorted(vif_list))
        else:
            log.info("No virtual interface device found.")
        exit(0)

    if options.add_index is not None:
        vif_index = options.add_index

        device_name = options.device
        if device_name is not None and device_name not in vnet_driver.get_all_devices():
            log.fail("Invalid device name:[%s].", device_name)
            exit(1)

        network = options.network
        if network is not None and network not in vnet_driver.get_network_list():
            log.fail("No network named: [%s].", network)
            exit(1)

        if options.device is None and options.network is None:
            device_name = virthost.get_default_device()
            if not device_name:
                log.fail("Failed to get default device. "
                         "Please specify a NIC or network for the new created virtual interface.")
                exit(1)

        if options.vif_ip is not None:
            if not virthost.is_IP_available(options.vif_ip, vif_netmask=options.vif_netmask, device=device_name):
                log.fail("IP check failed.")
                exit(1)

        if virthost.create_new_vif(inst_name, vif_index, device_name, network, options.vif_ip):
            log.success("New virtual interface device created successfully.")
            exit(0)
        else:
            log.fail("New virtual interface device created or attached failed.")
            exit(1)

    elif options.del_index is not None:
        vif_index = options.del_index

        ret = virthost.destroy_old_vif(inst_name, vif_index)
        if ret:
            log.success("Successfully delete the virtual interface device.")
            exit(0)
        else:
            log.fail("Failed to delete the virtual interface device")
            exit(1)

    elif options.vif_index is not None:
        vif_index = options.vif_index

        device_name = options.device
        if device_name is not None and device_name not in vnet_driver.get_all_devices():
            log.fail("Invalid device name:[%s].", device_name)
            exit(1)

        network = options.network
        if network is not None and network not in vnet_driver.get_network_list():
            log.fail("No network named: [%s].", network)
            exit(1)

        if options.device is None and options.network is None:
            device_name = virthost.get_default_device()
            if not device_name:
                log.fail("Failed to get default device. "
                         "Please specify a NIC or network for the new created virtual interface.")
                exit(1)

        if options.vif_ip is not None:
            if not virthost.is_IP_available(options.vif_ip, options.vif_netmask, device_name):
                log.fail("IP check failed.")
                exit(1)
        else:
            log.info("No IP specified, it will delete old VIF and create a new VIF to the target network.")

        if virthost.config_vif(inst_name, vif_index, device_name, network, options.vif_ip):
            log.success("New virtual interface device configured successfully.")
            exit(0)
        else:
            log.fail("New virtual interface device configured failed.")
            exit(1)

    elif options.disk_size is not None:

        if not options.storage_name:
            options.storage_name = virthost.get_max_free_size_storage()
            if not options.storage_name:
                log.fail("Failed to get default SR, please specify a storage name for the new virtual disk.")
                exit(1)

        size = int(options.disk_size)
        storage_info = virt_driver.get_host_storage_info(storage_name=options.storage_name)
        if not storage_info:
            log.fail("Fail to get infor about storage [%s]", options.storage_name)
            exit(1)
        if size >= storage_info['size_free'] - 1:
            log.fail("No enough volume on storage:[%s], at most [%s] GB is available",
                     options.storage_name, storage_info['size_free'] - 1)
            exit(1)

        ret = virthost.add_vm_disk(inst_name, storage_name=options.storage_name, size=size)
        if ret:
            log.success("Successfully add a new disk with size [%s]GB to VM [%s].", size, inst_name)
            exit(0)
        else:
            log.fail("Failed to add a new disk with size [%s]GB to VM [%s].", size, inst_name)
            exit(1)

    elif options.cpu_cores is not None or options.max_cores is not None:
        cpu_cores, max_cores = None, None
        try:
            if options.cpu_cores is not None:
                cpu_cores = int(options.cpu_cores)
            if options.max_cores is not None:
                max_cores = int(options.max_cores)
        except ValueError:
            log.fail("Please input a integer for cpu cores.")
            exit(1)

        ret = virthost.config_vcpus(inst_name, vcpu_nums=cpu_cores, vcpu_max=max_cores)
        if ret:
            log.success("Config VCPU cores successfully.")
            exit(0)
        else:
            log.fail("Config VCPU cores failed.")
            exit(1)

    elif options.memory_size is not None:
        try:
            memory_size = float(options.memory_size)
        except ValueError:
            log.fail("Please input a valid number for memory.")
            exit(1)

        if virt_driver.is_instance_running(inst_name):
            ret = virthost.config_memory_lively(inst_name, memory_size)
        elif virt_driver.is_instance_halted(inst_name):
            ret = virthost.config_memory(inst_name, static_max=memory_size, dynamic_max=memory_size)
        else:
            log.fail("The VM is not support configuring the memory in current state.")
            exit(1)
        if ret:
            log.success("Memory set successfully.")
            exit(0)
        else:
            log.fail("Memory set failed.")
            exit(1)
