#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: server_utils.py
 Author: longhui
 Created Time: 2018-03-13 18:41:44
 Descriptions: API to get information about the Server/Host
'''
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory
from lib.Utils.network_utils import IpCheck, is_IP_pingable


def print_server_hardware_info(**kwargs):
    """
    Display server hardware and platform info
    """
    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""
    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    log.info("General hardware and software information:")

    log.info("\nHost Manufacturer informations:")
    platform_info = virt_driver.get_host_plat_info()
    log.info("\tManufacturer: %s", platform_info.get('vendor_name'))
    log.info("\tModel: %s", platform_info.get('product_name'))
    log.info("\tSoftware Version: %s", virt_driver.get_host_sw_ver(short_name=False))

    log.info("\nHost CPU informations:")
    cpu_info = virt_driver.get_host_cpu_info()
    log.info("\tProcessor Model: %s", cpu_info.get("cpu_model"))
    log.info("\tProcessor Sockets: %s", cpu_info.get("cpu_sockets", 0))
    log.info("\tCores per Socket: %s", cpu_info.get("cores_per_socket", 0))
    log.info("\tThreads per Core: %s", cpu_info.get("thread_per_core", 1))
    log.info("\tLogical Processors: %s", cpu_info.get("cpu_cores"))
    log.info("\tProcessor Speed: %s MHz", cpu_info.get("cpu_speed"))

    log.info("\nHost Memory informations:")
    memory_info = virt_driver.get_host_mem_info()
    log.info("\tMemory total: %s GB", memory_info.get("size_total"))
    log.info("\tMemory used: %s GB", memory_info.get("size_used"))
    log.info("\tMemory free: %s GB", memory_info.get("size_free"))

    log.info("\nHost Default Storage informations:")
    storage_info = virt_driver.get_host_storage_info()
    log.info("\tStorage Size: %s GB", storage_info.get('size_total', 0))
    log.info("\tStorage Used: %s GB", storage_info.get('size_used', 0))
    log.info("\tStorage Free: %s GB", storage_info.get('size_free', 0))


def get_host_all_storage_info(**kwargs):
    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    storage_info = {}
    sr_list = virt_driver.get_host_all_storages()
    for sr in sr_list:
        size = virt_driver.get_host_storage_info(storage_name=sr)
        storage_info.setdefault(sr, [size['size_total'], size['size_free']])

    return storage_info


def get_default_device(host=None, user=None, passwd=None):
    """
    get the host's default network/Interface which has configured an IP;
    :param kwargs:
    :return: Interface name on host, or None
    """
    log.info("Get the host default network with IP configured.")

    host_name = host
    user = user if user else "root"
    passwd = str(passwd).replace('\\', '') if passwd else ""

    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)

    devices = vnet_driver.get_all_devices()
    for device_name in devices:
        # 'IP': '' or an ip,
        device_info = vnet_driver.get_device_infor(device_name=device_name)
        ipstr = device_info.get('IP', '')
        if ipstr:
            return device_name
    else:
        log.error("No device found with an IP configured.")
        return None


def get_default_storage(host=None, user=None, passwd=None):
    """
    get the default storage repository which has the largest volume for user
    :param host:
    :param user:
    :param passwd:
    :return: the storage name
    """
    log.info("Get the host default storage name which has the largest free volume.")

    host_name = host
    user = user if user else "root"
    passwd = str(passwd).replace('\\', '') if passwd else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    all_sr = virt_driver.get_host_all_storages()
    max_volume, target_sr = 0, None
    for sr in all_sr:
        storage_dict = virt_driver.get_host_storage_info(storage_name=sr)
        temp = int(storage_dict.get('size_free', 0))
        if temp > max_volume:
            max_volume, target_sr = temp, sr

    log.info("The default storage is '%s' with volume %s GB.", target_sr, max_volume)
    return target_sr


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
        log.error("Ipaddress [%s] is already be used(Ping test).", vif_ip)
        return False

    return True


if __name__ == "__main__":
    d = get_host_all_storage_info(host="10.143.248.16", user="root", passwd="Mojiti!906")
    for k, v in d.iteritems():
        print k, "\t\t", v
