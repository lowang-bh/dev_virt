#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: scripts/config_vm.py
 Author: longhui
 Created Time: 2018-03-07 09:38:18
'''

from optparse import OptionParser
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory, VM_MAC_PREFIX
from lib.Utils.vm_utils import is_IP_available, create_new_vif, destroy_old_vif, config_vif

if __name__ == "__main__":
    usage = """usage: %prog [options] vm_name\n
        config_vm.py vm_name --add-vif=vif_index --device=eth0  [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --del-vif=vif_index   [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --vif=vif_index --device=eth0 --ip=ip [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --list-vif            [--host=ip --user=user --pwd=passwd]
        config_vm.py vm_name --list-pif            [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    parser.add_option("--add-vif", dest="add_index", help="Add a virtual interface device to guest VM")
    parser.add_option("--del-vif", dest="del_index", help="Delete a virtual interface device from guest VM")
    parser.add_option("--vif", dest="vif_index", help="Configurate on a virtual interface device")

    parser.add_option("--device", dest="device", help="The target physic NIC name with an associated network vif attach(ed) to")
    parser.add_option("--network", dest="network", help="The target bridge/switch network which vif connect(ed) to")
    parser.add_option("--ip", dest="vif_ip", help="The ip assigned to the virtual interface")
    parser.add_option("--netmask", dest="vif_netmask", help="The netmask for the target virtual interface")

    parser.add_option("--list-vif", dest="list_vif", action="store_true",
                      help="List the virtual interface device in guest VM")
    parser.add_option("--list-pif", dest="list_pif", action="store_true",
                      help="List the interface device in the host")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    if not args:
        log.error("Please specify a VM name to config.")
        parser.print_help()
        exit(1)
    if not options.list_vif  and not options.list_pif and \
        (not options.vif_index and not options.del_index and not options.add_index):
        parser.print_help()
        exit(1)

    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)
    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
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

    if options.list_pif:
        pif_list = vnet_driver.get_all_devices()
        if pif_list:
            log.info("All device on the host: %s", sorted(pif_list))
        else:
            log.info("No device found on the host.")

    if options.add_index is not None:
        vif_index = options.add_index
        if options.device is None and options.network is None:
            log.fail("Please specify a NIC or network for the new created virtual interface.")
            exit(1)
        device_name = options.device
        if device_name and device_name not in vnet_driver.get_all_devices():
            log.fail("Invalid device name:[%s].", device_name)
            exit(1)

        network = options.network
        if network and network not in vnet_driver.get_vswitch_list():
            log.fail("No network named: [%s].", network)
            exit(1)

        mac_addr = None

        option_dic = {"vif_ip":options.vif_ip, "vif_netmask":options.vif_netmask,
                      "device":options.device, "host":options.host,
                      "user":options.user, "passwd":options.passwd}
        if options.vif_ip:
            if not is_IP_available(**option_dic):
                log.fail("IP check failed.")
                exit(1)
            mac_strs = ['%02x' % int(num) for num in options.vif_ip.split(".")]
            mac_addr = VM_MAC_PREFIX + ":%s:%s:%s:%s" % tuple(mac_strs)

        if create_new_vif(inst_name, vif_index, device_name, network, mac_addr, **option_dic):
            log.success("New virtual interface device created successfully.")
            exit(0)
        else:
            log.fail("New virtual interface device created or attached failed.")
            exit(1)
    elif options.del_index is not None:
        vif_index = options.del_index

        option_dic = {"host":options.host, "user":options.user, "passwd":options.passwd}
        ret = destroy_old_vif(inst_name, vif_index, **option_dic)
        if ret:
            log.success("Successfully delete the virtual interface device.")
            exit(0)
        else:
            log.fail("Failed to delete the virtual interface device")
            exit(1)
    elif options.vif_index is not None:
        vif_index = options.vif_index
        if options.device is None and options.network is None:
            log.fail("Please specify a NIC or bridge for the new configured virtual interface.")
            exit(1)

        device_name = options.device
        if device_name and device_name not in vnet_driver.get_all_devices():
            log.fail("Invalid device name:[%s].", device_name)
            exit(1)

        network = options.network
        if network and network not in vnet_driver.get_vswitch_list():
            log.fail("No network named: [%s].", network)
            exit(1)

        mac_addr = None
        option_dic = {"vif_ip":options.vif_ip, "vif_netmask":options.vif_netmask,
                      "device":options.device, "host":options.host,
                      "user":options.user, "passwd":options.passwd}

        if options.vif_ip is not None:
            if not is_IP_available(**option_dic):
                log.fail("IP check failed.")
                exit(1)
            mac_strs = ['%02x' % int(num) for num in options.vif_ip.split(".")]
            mac_addr = VM_MAC_PREFIX + ":%s:%s:%s:%s" % tuple(mac_strs)
        else:
            log.info("No IP specified, it will delete old VIF and create a new VIF to the target network.")

        if config_vif(inst_name, vif_index, device_name, network, mac_addr, **option_dic):
            log.success("New virtual interface device configured successfully.")
            exit(0)
        else:
            log.fail("New virtual interface device configured failed.")
            exit(1)
