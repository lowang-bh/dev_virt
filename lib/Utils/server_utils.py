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
    log.info("\tLogical Processors: %s", cpu_info.get("cpu_cores"))
    log.info("\tProcessor Speed: %s MHz", cpu_info.get("cpu_speed"))

    log.info("\nHost Memory informations:")
    memory_info = virt_driver.get_host_mem_info()
    log.info("\tMemory total: %s GB", memory_info.get("size_total"))
    log.info("\tMemory used: %s GB", memory_info.get("size_used"))
    log.info("\tMemory free: %s GB", memory_info.get("size_free"))

    log.info("\nHost Default Storage informations:")
    storage_info =virt_driver.get_host_storage_info()
    log.info("\tStorage Size: %s GB", storage_info.get('size_total', 0))
    log.info("\tStorage Used: %s GB", storage_info.get('size_used', 0))
    log.info("\tStorage Free: %s GB", storage_info.get('size_free', 0))
