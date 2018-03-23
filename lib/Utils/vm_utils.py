#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vm_utils.py
 Author: longhui
 Created Time: 2018-03-07 17:28:19
'''
from lib.Utils.network_utils import IpCheck, is_IP_pingable
from lib.Val.virt_factory import VirtFactory
from lib.Log.log import log


def is_IP_available(vif_ip=None, vif_netmask=None, device=None, **kwargs):
    """
    check if a IP and Netmask usable
    """
    # No ip , don't need to check
    if not vif_ip:
        return True

    dest_metmask = ""
    dest_gateway = None
    if device is not None:
        try:
            host_name = kwargs['host']
            user = kwargs['user'] if kwargs['user'] else "root"
            passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""
            vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)
            device_info = vnet_driver.get_device_infor(device_name=device)
            dest_metmask = device_info["netmask"]
            dest_gateway = device_info['gateway']
        except KeyError, error:
            log.exception(str(error))

    if vif_netmask:
        if dest_metmask and dest_metmask != vif_netmask:
            log.error("Netmask [%s] is not corresponding with the target network.", vif_netmask)
            return False
    else:  # get the netmask on device as the default one
        vif_netmask = dest_metmask
    log.debug("VIF IP is: %s, netmask is: %s", vif_ip, vif_netmask)
    if not vif_netmask:  # No default netmask and no given
        log.error("No netmask given, please specify one.")
        return False

    vif_gateway = dest_gateway if dest_gateway else None
    if not IpCheck.is_valid_ipv4_parameter(vif_ip, vif_netmask, gateway=vif_gateway):
        return False

    if is_IP_pingable(vif_ip):
        log.error("Ipaddress [%s] is already be used.", vif_ip)
        return False

    return True


def create_new_vif(inst_name, vif_index, device_name=None, network=None, mac_addr=None, **kwargs):
    """
    create a new virtual interface on the target VM
    @param inst_name: Vm name
    @param device_name: vswitch (with the host-device attached) which the vif attach to
    @param vif_index: vif index
    """
    log.info("Start to add a new virtual interface device with index:[%s] to VM [%s]", vif_index, inst_name)

    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""
    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)

    new_vif = vnet_driver.create_new_vif(inst_name, vif_index, device_name, network, MAC=mac_addr)
    if new_vif is not None:
        if VirtFactory.get_virt_driver(host_name, user, passwd).is_instance_running(inst_name):
            ret = vnet_driver.plug_vif_to_vm(inst_name, vif_index)
            if ret:
                log.info("New virtual interface device [%s] attached to VM [%s] successfully.", vif_index, inst_name)
                return True
            else:
                log.error("New virtual interface device attached failed to VM [%s].", inst_name)
                return False
        else:
            log.info("New virtual interface device created successfully, but didn't plugin as VM is power off.")
            return True

    log.error("Can not create new virtual interface device [%s].", vif_index)
    return False


def destroy_old_vif(inst_name, vif_index, **kwargs):
    """
    Destroy old vif whose index is vif_index
    @param inst_name: Vm name
    @param vif_index: vif index
    """
    log.info("Start to delete the old interface device [%s] from VM [%s].", vif_index, inst_name)

    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""
    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)

    if not vnet_driver.is_vif_exist(inst_name, vif_index):
        log.info("No old vif with index [%s], don't need to destroy.", vif_index)
        return True

    if VirtFactory.get_virt_driver(host_name, user, passwd).is_instance_running(inst_name):
        ret = vnet_driver.unplug_vif_from_vm(inst_name, vif_index)
        if not ret:
            log.error("Failed to unplug the virtual interface device [%s] from VM.", vif_index)
            return False
    ret = vnet_driver.destroy_vif(inst_name, vif_index)
    if not ret:
        log.error("Failed to destroy the virtual interface device [%s].", vif_index)
        return False

    return True


def config_vif(inst_name, vif_index, device_name=None, network=None, mac_addr=None, **kwargs):
    """
    configure a vif: first destroy old vif and then create a new vif
    @param inst_name: Vm name
    @param device_name: vswitch (with the host-device attached) which the vif attach to
    @param vif_index: vif index
    """
    log.info("Start to configure the interface device [%s] in VM [%s].", vif_index, inst_name)

    if not destroy_old_vif(inst_name, vif_index, **kwargs):
        return False

    ret = create_new_vif(inst_name, vif_index, device_name, network, mac_addr, **kwargs)

    return ret


def get_all_vifs_info(inst_name, **kwargs):
    """
    :param inst_name:
    :param kwargs:
    :return: A dict with key is vif index and value is mac, ip, etc
    """
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)

    vif_indexes = vnet_driver.get_all_vifs_indexes(inst_name=inst_name)
    vifs_info = {}

    for vif_index in vif_indexes:
        vifs_info.setdefault(vif_index, vnet_driver.get_vif_info(inst_name, vif_index))

    return vifs_info


def print_all_vifs_info(inst_name, **kwargs):
    """
    :param inst_name:
    :param kwargs:
    :return:
    """
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    log.info("All Vifs information with vif index number and MAC, IP:")

    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)

    vifs_info = vnet_driver.get_all_vif_info(inst_name=inst_name)
    for vif_index in vifs_info:
        log.info("\t%s\tMAC: %s, IP: %s", vif_index, vifs_info[vif_index]['mac'], vifs_info[vif_index]['ip'])

    return True


def get_all_disk_info(inst_name, **kwargs):
    """
    return a dict with its key is disk number and value is disk size of GB
    :param inst_name:
    :return:
    """
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    disk_info = {}
    disk_dict = virt_driver.get_all_disk(inst_name=inst_name)
    for disk_num in disk_dict:
        size = str(virt_driver.get_disk_size(inst_name=inst_name, device_num=disk_num)) + " GB"
        disk_info.setdefault(disk_num, size)

    return disk_info


def print_vm_disk_info(inst_name, **kwargs):
    """
    :param inst_name:
    :param kwargs:
    :return:
    """
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    log.info("All disk information with disk number and size(GB):")

    disk_dict = virt_driver.get_all_disk(inst_name=inst_name)
    for disk_num in sorted(disk_dict):
        size = str(virt_driver.get_disk_size(inst_name=inst_name, device_num=disk_num)) + " GB"
        log.info("\t%s\t%s", disk_num, size)


def print_vm_info(inst_name, **kwargs):
    """
    :param inst_name:
    :param kwargs: host, user, passwd
    :return:
    """
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    log.info("General hardware and software information for VM: [%s]", inst_name)

    vm_record = virt_driver.get_vm_record(inst_name)

    log.info("VM CPU informations:")
    log.info("Max Vcpus: %s\n", vm_record.get("VCPUs_max"))

    log.info("VM memory informations:")
    log.info("Dynamic Memory: Max: %-4s GB, Min: %-4s GB", vm_record.get("memory_dynamic_max"), vm_record.get("memory_dynamic_min"))
    log.info("Static  Memory: Max: %-4s GB, Min: %-4s GB", vm_record.get("memory_static_max"), vm_record.get("memory_static_min"))
    log.info("Current memory: %s GB\n", vm_record.get("memory_target", 0))

    log.info("VM OS informations:")
    log.info("OS type: %s\n", virt_driver.get_os_type(inst_name, short_name=False))

    # log.info("\nHost Default Storage informations:")


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))
    print get_all_disk_info(inst_name="test2", host=options.host, user=options.user, passwd=options.passwd)
    print get_all_vifs_info(inst_name="test2", host=options.host, user=options.user, passwd=options.passwd)
