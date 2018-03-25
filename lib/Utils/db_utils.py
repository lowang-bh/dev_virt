#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: db_utils.py
 Author: longhui
 Created Time: 2018-03-22 20:30:55
 Descriptions: This file is used to update information to databse, don't care about which table
'''

from lib.Log.log import log
from lib.Db.db_factory import DbFactory
from lib.Val.virt_factory import VirtFactory


def create_vm_database_info(inst_name, **kwargs):
    """

    :param inst_name: VM name
    :param kwargs: host, user, passwd dict
    :return:
    """
    log.info("Start to create [%s] information to databse.", inst_name)

    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    db_driver = DbFactory.get_db_driver("VirtHost")

    vm_record = virt_driver.get_vm_record(inst_name=inst_name)
    if not vm_record:
        return False

    hostname = inst_name
    sn = vm_record['uuid']
    cpu_cores = vm_record['VCPUs_live']
    memory_size = vm_record['memory_target']

    disk_info = virt_driver.get_all_disk(inst_name=inst_name)
    disk_num = len(disk_info)
    disk_size = virt_driver.get_disk_size(inst_name, 0)  # only write the system disk size when create
    # for disk in disk_info:
    #     disk_size += virt_driver.get_disk_size(inst_name, disk)

    ret = db_driver.create(hostname, sn, cpu_cores, memory_size, disk_size, disk_num)
    if ret:
        log.info("Create record to database successfully.")
    else:
        log.error("Create record to database failed.")

    return ret


def delete_vm_database_info(inst_name):
    """
    delete from database with VM name is inst_name
    :param inst_name:
    :return:
    """
    log.info("Start to delete [%s] information from databse.", inst_name)

    db_driver = DbFactory.get_db_driver("VirtHost")
    return db_driver.delete(hostname=inst_name)


def update_vm_database_info(inst_name, **kwargs):
    """
    This function is used to sync VM information when config changed,include :cpu_cores, memory_size, disk_num
    :param inst_name:
    :param kwargs:
    :return:
    """
    log.info("Start to update [%s] information to databse.", inst_name)

    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)
    db_driver = DbFactory.get_db_driver("VirtHost")

    vm_record = virt_driver.get_vm_record(inst_name=inst_name)
    if not vm_record:
        return False

    sn = vm_record['uuid']
    cpu_cores = vm_record['VCPUs_live']
    memory_size = vm_record['memory_target']

    disk_info = virt_driver.get_all_disk(inst_name=inst_name)
    disk_num = len(disk_info)

    vif_dic = vnet_driver.get_all_vif_info(inst_name)
    first_ip = vif_dic.get('0', {}).get('ip', None)
    #second_ip is local ip
    #second_ip = vif_dic.get('1', {}).get('ip', None)
    # TODO: sync disk size, and VIF infor
    #disk_size = virt_driver.get_disk_size(inst_name, 0)  # only write the system disk size when create
    # for disk in disk_info:
    #     disk_size += virt_driver.get_disk_size(inst_name, disk)
    sync_data = {"cpu_cores": cpu_cores,
                 "memory_size": memory_size,
                 "disk_num": disk_num,
                 "first_ip": first_ip
                 }

    try:
        ret = db_driver.update(sn=sn, data=sync_data)
    except Exception:
        ret = False
    if not ret:
        log.warn("Update database information with ret: [%], data: %s", ret, sync_data)

    return ret


def update_memory_to_database(inst_name, **kwargs):
    """
    :param inst_name:
    :param kwargs:
    :return:
    """
    log.info("Update [%s] memory information to database.", inst_name)
    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    db_driver = DbFactory.get_db_driver("VirtHost")

    vm_record = virt_driver.get_vm_record(inst_name=inst_name)
    if not vm_record:
        return False
    memory_size = vm_record['memory_target']
    sn = vm_record['uuid']

    return db_driver.update(sn=sn, data={"memory_size":memory_size})


def update_vcpu_to_database(inst_name, **kwargs):
    """
    :param inst_name:
    :return:
    """
    log.info("Update [%s] VCPU information to database.", inst_name)
    host_name = kwargs['host']
    user = kwargs['user'] if kwargs['user'] else "root"
    passwd = str(kwargs['passwd']).replace('\\', '') if kwargs['passwd'] else ""

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    db_driver = DbFactory.get_db_driver("VirtHost")

    vm_record = virt_driver.get_vm_record(inst_name=inst_name)
    if not vm_record:
        return False
    cpu_cores = vm_record['VCPUs_live']
    sn = vm_record['uuid']

    return db_driver.update(sn=sn, data={"cpu_cores": cpu_cores})


def update_vif_to_database(inst_name, *kwargs):
    """
    :param inst_name:
    :param kwargs:
    :return:
    """
    log.info("Update %s vif information to database.", inst_name)

    raise NotImplementedError()



if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    parser.add_option("--create", dest="create", help="Create VM record in database")
    parser.add_option("--delete", dest="delete", help="Delete record from database")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)

    if options.create:
        print create_vm_database_info(inst_name=options.create, host=options.host, user=options.user, passwd=options.passwd)
    elif options.delete:
        print delete_vm_database_info(inst_name=options.delete)
    else:
        parser.print_help()
