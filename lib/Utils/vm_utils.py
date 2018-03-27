#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vm_utils.py
 Author: longhui
 Created Time: 2018-03-07 17:28:19
 Descriptions: This is the common utils for the CLI to use, do config to VM in this utils will not check
        the return value of update_database, except create/delete VM
'''

from lib.Val.virt_factory import VirtFactory, VM_MAC_PREFIX
from lib.Log.log import log
from lib.Utils.db_utils import update_vm_database_info, create_vm_database_info, delete_vm_database_info,\
    update_ip_infor_to_database, delete_ip_info_from_database


def create_vm(new_vm_name, template_name, **kwargs):
    """
    Create new instance with name and template
    :param new_vm_name:
    :param template_name:
    :param kwargs:
    :return:
    """
    log.info("Start to create new instance: [%s], with template:[%s]", new_vm_name, template_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    ret = virt_driver.create_instance(new_vm_name, template_name)
    if not ret:
        return False

    db_ret = create_vm_database_info(inst_name=new_vm_name, **kwargs)

    return db_ret


def delete_vm(vm_name, **kwargs):
    """
    :param vm_name:
    :param kwargs:
    :return:
    """
    log.info("Start to delete VM [%s].", vm_name)

    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    ret = virt_driver.delete_instance(vm_name)
    if not ret:
        return False

    db_ret = delete_vm_database_info(inst_name=vm_name)
    if not db_ret:
        log.warn("Failed to clear the database information of VM [%s], please do it manually.", vm_name)

    # No matter delete vm from DB failed or not, return True
    return True


def create_new_vif(inst_name, vif_index, device_name=None, network=None, ip=None, **kwargs):
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

    if ip:
        mac_strs = ['%02x' % int(num) for num in ip.split(".")]
        mac_addr = VM_MAC_PREFIX + ":%s:%s:%s:%s" % tuple(mac_strs)
    else:
        mac_addr = None

    log.debug("Create VIF [%s] with IP: %s,  MAC: %s.", vif_index, ip, mac_addr)
    new_vif = vnet_driver.create_new_vif(inst_name, vif_index, device_name, network, MAC=mac_addr)
    if new_vif is not None:

        update_ip_infor_to_database(inst_name, vif_index=vif_index, ip=ip)

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

    delete_ip_info_from_database(inst_name, vif_index)

    return True


def config_vif(inst_name, vif_index, device_name=None, network=None, ip=None, **kwargs):
    """
    configure a vif: first destroy old vif and then create a new vif
    @param inst_name: Vm name
    @param device_name: vswitch (with the host-device attached) which the vif attach to
    @param vif_index: vif index
    """
    log.info("Start to configure the interface device [%s] in VM [%s].", vif_index, inst_name)

    if not destroy_old_vif(inst_name, vif_index, **kwargs):
        return False

    ret = create_new_vif(inst_name, vif_index, device_name, network, ip, **kwargs)

    return ret


def config_vcpus(inst_name, vcpu_nums=None, vcpu_max=None, **kwargs):
    """
    :param inst_name: VM name
    :param vcpu_nums: the current vcpu number
    :param vcpu_max: the max vcpu  number
    :return:
    """
    log.info("Start to configure the VCPU in VM [%s].", inst_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']
    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)

    if vcpu_nums and virt_driver.is_instance_running(inst_name=inst_name):
        ret = virt_driver.set_vm_vcpu_live(inst_name=inst_name, vcpu_num=vcpu_nums)

    elif vcpu_max and virt_driver.is_instance_halted(inst_name=inst_name):
        ret = virt_driver.set_vm_vcpu_max(inst_name=inst_name, vcpu_num=vcpu_max)

    else:
        log.error("Only support set live cpu on a running VM  or set max cpu number on a halted VM.")
        return False
    # set vcpu max will change the start up vcpu when max < live cpu number
    if ret:
        # Don't need to check db sync ret, because there is crontab to sync it
        update_vm_database_info(inst_name=inst_name, **kwargs)

    return ret


def power_on_vm(vm_name, **kwargs):
    """
    :param vm_name:
    :param kwargs:
    :return:
    """
    log.info("Start to power on VM [%s].", vm_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    if virt_driver.is_instance_running(inst_name=vm_name):
        log.info("VM [%s] is already running.", vm_name)
        return True

    ret = virt_driver.power_on_vm(vm_name)

    if ret:
        update_vm_database_info(vm_name, **kwargs)

    return ret


def power_off_vm(vm_name, **kwargs):
    """
    :param vm_name:
    :param kwargs:
    :return:
    """
    log.info("Start to power off VM [%s].", vm_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    if virt_driver.is_instance_halted(inst_name=vm_name):
        log.info("VM [%s] is already power off.", vm_name)
        return True

    ret = virt_driver.power_off_vm(vm_name)

    if ret:
        update_vm_database_info(vm_name, **kwargs)

    return ret


def reset_vm(vm_name, **kwargs):
    """
    :param vm_name:
    :return:
    """
    log.info("Start to reset [%s]", vm_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    ret = virt_driver.reboot(vm_name)

    return ret


def add_vm_disk(inst_name, storage_name, size, **kwargs):
    """
    :param inst_name: VM name
    :param storage_name: the storage repository name, in KVM, it is pool name
    :param size: virtual disk size in GB
    :param kwargs: login information
    :return: True or False
    """
    log.info("Start to add a vdisk with size [%s]GB to VM [%s].", size, inst_name)
    host_name = kwargs['host']
    user = kwargs['user']
    passwd = kwargs['passwd']

    virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
    ret = virt_driver.add_vdisk_to_vm(inst_name, storage_name, size=size)

    if ret:
        update_vm_database_info(inst_name=inst_name, **kwargs)

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
    for vif_index in sorted(vifs_info):
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
    log.info("Max Vcpus: %s, Current Vcpus: %s\n", vm_record.get("VCPUs_max"), vm_record.get("VCPUs_live"))

    log.info("VM memory informations:")
    log.info("Dynamic Memory: Max: %4s GB, Min: %4s GB", vm_record.get("memory_dynamic_max"), vm_record.get("memory_dynamic_min"))
    log.info("Static  Memory: Max: %4s GB, Min: %4s GB", vm_record.get("memory_static_max"), vm_record.get("memory_static_min"))
    log.info("Target  Memory: %4s GB, Actual Memory: %4s GB\n", vm_record.get("memory_target", 0), vm_record['memory_actual'])

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
