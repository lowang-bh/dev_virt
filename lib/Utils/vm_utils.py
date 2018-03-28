#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: vm_utils.py
 Author: longhui
 Created Time: 2018-03-07 17:28:19
 Descriptions: This is the common utils for the CLI to use, do config to VM in this utils will not check
        the return value of update_database, except create/delete VM
"""

from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory, VM_MAC_PREFIX
from lib.Db.db_factory import DbFactory
from lib.Utils.server_utils import ServerDomain


class VirtHostDomain(ServerDomain):
    def __init__(self, host_name=None, user="root", passwd=""):
        self.virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        self.vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)
        self.db_driver = DbFactory.get_db_driver("VirtHost")

    def create_vm(self, new_vm_name, template_name):
        """
        Create new instance with name and template
        :param new_vm_name:
        :param template_name:
        :return:
        """
        ret = self.virt_driver.create_instance(new_vm_name, template_name)
        if not ret:
            return False

        db_ret = self.create_database_info(inst_name=new_vm_name)

        return db_ret

    def delete_vm(self, vm_name):
        """
        :param vm_name:
        :return:
        """
        log.info("Start to delete VM [%s].", vm_name)

        ret = self.virt_driver.delete_instance(vm_name)
        if not ret:
            return False

        db_ret = self.delete_database_info(inst_name=vm_name)
        if not db_ret:
            log.warn("Failed to clear the database information of VM [%s], please do it manually.", vm_name)

        # No matter delete vm from DB failed or not, return True
        return True

    def create_new_vif(self, inst_name, vif_index, device_name=None, network=None, ip=None):
        """
        create a new virtual interface on the target VM
        @param inst_name: Vm name
        @param device_name: vswitch (with the host-device attached) which the vif attach to
        @param vif_index: vif index
        @param network
        @param ip
        """
        log.info("Start to add a new virtual interface device with index:[%s] to VM [%s]", vif_index, inst_name)

        if ip:
            mac_strs = ['%02x' % int(num) for num in ip.split(".")]
            mac_addr = VM_MAC_PREFIX + ":%s:%s:%s:%s" % tuple(mac_strs)
        else:
            mac_addr = None

        log.debug("Create VIF [%s] with IP: %s,  MAC: %s.", vif_index, ip, mac_addr)
        new_vif = self.vnet_driver.create_new_vif(inst_name, vif_index, device_name, network, MAC=mac_addr)
        if new_vif is not None:

            self.update_ip_infor_to_database(inst_name, vif_index=vif_index, ip=ip)

            if self.virt_driver.is_instance_running(inst_name):
                ret = self.vnet_driver.plug_vif_to_vm(inst_name, vif_index)
                if ret:
                    log.info("New virtual interface device [%s] attached to VM [%s] successfully.",
                             vif_index, inst_name)
                    return True
                else:
                    log.error("New virtual interface device attached failed to VM [%s].", inst_name)
                    return False
            else:
                log.info("New virtual interface device created successfully, but didn't plugin as VM is power off.")
                return True

        log.error("Can not create new virtual interface device [%s].", vif_index)
        return False

    def destroy_old_vif(self, inst_name, vif_index):
        """
        Destroy old vif whose index is vif_index
        @param inst_name: Vm name
        @param vif_index: vif index
        """
        log.info("Start to delete the old interface device [%s] from VM [%s].", vif_index, inst_name)

        if not self.vnet_driver.is_vif_exist(inst_name, vif_index):
            log.info("No old vif with index [%s], don't need to destroy.", vif_index)
            return True

        if self.virt_driver.is_instance_running(inst_name):
            ret = self.vnet_driver.unplug_vif_from_vm(inst_name, vif_index)
            if not ret:
                log.error("Failed to unplug the virtual interface device [%s] from VM.", vif_index)
                return False
        ret = self.vnet_driver.destroy_vif(inst_name, vif_index)
        if not ret:
            log.error("Failed to destroy the virtual interface device [%s].", vif_index)
            return False

        self.delete_ip_info_from_database(inst_name, vif_index)

        return True

    def config_vif(self, inst_name, vif_index, device_name=None, network=None, ip=None):
        """
        configure a vif: first destroy old vif and then create a new vif
        @param inst_name: Vm name
        @param device_name: vswitch (with the host-device attached) which the vif attach to
        @param vif_index: vif index
        @param network:
        @param ip:
        """
        log.info("Start to configure the interface device [%s] in VM [%s].", vif_index, inst_name)

        if not self.destroy_old_vif(inst_name, vif_index):
            return False

        ret = self.create_new_vif(inst_name, vif_index, device_name, network, ip)

        return ret

    def config_vcpus(self, inst_name, vcpu_nums=None, vcpu_max=None):
        """
        :param inst_name: VM name
        :param vcpu_nums: the current vcpu number
        :param vcpu_max: the max vcpu  number
        :return:
        """
        log.info("Start to configure the VCPU in VM [%s].", inst_name)

        if vcpu_nums and self.virt_driver.is_instance_running(inst_name=inst_name):
            ret = self.virt_driver.set_vm_vcpu_live(inst_name=inst_name, vcpu_num=vcpu_nums)

        elif vcpu_max and self.virt_driver.is_instance_halted(inst_name=inst_name):
            ret = self.virt_driver.set_vm_vcpu_max(inst_name=inst_name, vcpu_num=vcpu_max)

        else:
            log.error("Only support set live cpu on a running VM  or set max cpu number on a halted VM.")
            return False
        # set vcpu max will change the start up vcpu when max < live cpu number
        if ret:
            # Don't need to check db sync ret, because there is crontab to sync it
            self.update_database_info(inst_name=inst_name)

        return ret

    def config_memory(self, inst_name, static_max=None, static_min=None, dynamic_max=None, dynamic_min=None):
        """
        Memory limits must satisfy: static_min <= dynamic_min <= dynamic_max <= static_max
        :param inst_name:
        :param static_max:
        :param static_min:
        :param dynamic_max:
        :param dynamic_min:
        :return:
        """
        log.info("Start to config the memory in VM[%s]", inst_name)
        if static_max or static_min:
            ret = self.virt_driver.set_vm_static_memory(inst_name, memory_max=static_max, memory_min=static_min)
            if not ret:
                return False
        if dynamic_max or dynamic_min:
            ret = self.virt_driver.set_vm_dynamic_memory(inst_name, memory_max=dynamic_max, memory_min=dynamic_min)
            if not ret:
                return False
        return True

    def power_on_vm(self, vm_name):
        """
        :param vm_name:
        :return:
        """
        log.info("Start to power on VM [%s].", vm_name)

        if self.virt_driver.is_instance_running(inst_name=vm_name):
            log.info("VM [%s] is already running.", vm_name)
            return True

        ret = self.virt_driver.power_on_vm(vm_name)

        if ret:
            self.update_database_info(vm_name)

        return ret

    def power_off_vm(self, vm_name):
        """
        :param vm_name:
        :return:
        """
        log.info("Start to power off VM [%s].", vm_name)

        if self.virt_driver.is_instance_halted(inst_name=vm_name):
            log.info("VM [%s] is already power off.", vm_name)
            return True

        ret = self.virt_driver.power_off_vm(vm_name)

        if ret:
            self.update_database_info(vm_name)

        return ret

    def reset_vm(self, vm_name):
        """
        :param vm_name:
        :return:
        """
        log.info("Start to reset [%s]", vm_name)

        ret = self.virt_driver.reboot(vm_name)

        return ret

    def add_vm_disk(self, inst_name, storage_name, size):
        """
        :param inst_name: VM name
        :param storage_name: the storage repository name, in KVM, it is pool name
        :param size: virtual disk size in GB
        :return: True or False
        """
        log.info("Start to add a vdisk with size [%s]GB to VM [%s].", size, inst_name)

        ret = self.virt_driver.add_vdisk_to_vm(inst_name, storage_name, size=size)

        if ret:
            self.update_database_info(inst_name=inst_name)

        return ret

    def get_all_vifs_info(self, inst_name):
        """
        :param inst_name:
        :return: A dict with key is vif index and value is mac, ip, etc
        """
        vif_indexes = self.vnet_driver.get_all_vifs_indexes(inst_name=inst_name)
        vifs_info = {}

        for vif_index in vif_indexes:
            vifs_info.setdefault(vif_index, self.vnet_driver.get_vif_info(inst_name, vif_index))

        return vifs_info

    def print_all_vifs_info(self, inst_name):
        """
        :param inst_name:
        :return:
        """
        log.info("All Vifs information with vif index number and MAC, IP:")

        vifs_info = self.vnet_driver.get_all_vif_info(inst_name=inst_name)
        for vif_index in sorted(vifs_info):
            log.info("\t%s\tMAC: %s, IP: %s", vif_index, vifs_info[vif_index]['mac'], vifs_info[vif_index]['ip'])

        return True

    def get_all_disk_info(self, inst_name):
        """
        return a dict with its key is disk number and value is disk size of GB
        :param inst_name:
        :return:
        """

        disk_info = {}
        disk_dict = self.virt_driver.get_all_disk(inst_name=inst_name)
        for disk_num in disk_dict:
            size = str(self.virt_driver.get_disk_size(inst_name=inst_name, device_num=disk_num)) + " GB"
            disk_info.setdefault(disk_num, size)

        return disk_info

    def print_vm_disk_info(self, inst_name):
        """
        :param inst_name:
        :return:
        """

        log.info("All disk information with disk number and size(GB):")

        disk_dict = self.virt_driver.get_all_disk(inst_name=inst_name)
        for disk_num in sorted(disk_dict):
            size = str(self.virt_driver.get_disk_size(inst_name=inst_name, device_num=disk_num)) + " GB"
            log.info("\t%s\t%s", disk_num, size)

    def print_vm_info(self, inst_name):
        """
        :param inst_name:
        :return:
        """
        log.info("General hardware and software information for VM: [%s]", inst_name)

        vm_record = self.virt_driver.get_vm_record(inst_name)

        log.info("VM CPU informations:")
        log.info("Max Vcpus: %s, Current Vcpus: %s\n", vm_record.get("VCPUs_max"), vm_record.get("VCPUs_live"))

        log.info("VM memory informations:")
        log.info("Dynamic Memory: Max: %4s GB, Min: %4s GB", vm_record.get("memory_dynamic_max"),
                 vm_record.get("memory_dynamic_min"))
        log.info("Static  Memory: Max: %4s GB, Min: %4s GB", vm_record.get("memory_static_max"),
                 vm_record.get("memory_static_min"))
        log.info("Target  Memory: %4s GB, Actual Memory: %4s GB\n", vm_record.get("memory_target", 0),
                 vm_record['memory_actual'])

        log.info("VM OS informations:")
        log.info("OS type: %s\n", self.virt_driver.get_os_type(inst_name, short_name=False))

        # log.info("\nHost Default Storage informations:")

    def create_database_info(self, inst_name):
        """
        :param inst_name: VM name
        :return:
        """
        log.info("Start to create [%s] information to databse.", inst_name)

        vm_record = self.virt_driver.get_vm_record(inst_name=inst_name)
        if not vm_record:
            return False

        sn = vm_record['uuid']
        if self.db_driver.query(sn=sn):
            log.info("Record with given VM:[%s] exist, don't create record to database", inst_name)
            return True

        hostname = inst_name
        sn = vm_record['uuid']
        cpu_cores = vm_record['VCPUs_live']
        memory_size = vm_record['memory_target']

        disk_info = self.virt_driver.get_all_disk(inst_name=inst_name)
        disk_num = len(disk_info)
        disk_size = self.virt_driver.get_disk_size(inst_name, 0)  # only write the system disk size when create

        vm_host_ip = self.vnet_driver.get_host_manage_interface_infor()['IP']

        ret = self.db_driver.create(hostname, sn, cpu_cores, int(memory_size), int(disk_size), disk_num, vm_host_ip=vm_host_ip)
        if ret:
            log.info("Create record to database successfully.")
        else:
            log.error("Create record to database failed.")

        return ret

    def delete_database_info(self, inst_name):
        """
        delete from database with VM name is inst_name
        :param inst_name:
        :return:
        """
        log.info("Start to delete [%s] information from databse.", inst_name)

        return self.db_driver.delete(hostname=inst_name)

    def update_database_info(self, inst_name):
        """
        This function is used to sync VM information when config changed, include:cpu_cores, memory_size, disk_num
        :param inst_name:
        :return:
        """
        log.info("Start to update [%s] information to databse.", inst_name)

        vm_record = self.virt_driver.get_vm_record(inst_name=inst_name)
        if not vm_record:
            return False

        sn = vm_record['uuid']
        if not self.db_driver.query(sn=sn):
            log.info("No record found with given VM:[%s], don't update database", inst_name)
            return True

        cpu_cores = vm_record['VCPUs_live']
        memory_size = vm_record['memory_target']

        disk_info = self.virt_driver.get_all_disk(inst_name=inst_name)
        disk_num = len(disk_info)

        vif_dic = self.vnet_driver.get_all_vif_info(inst_name)
        first_ip = vif_dic.get('0', {}).get('ip', None)
        # second_ip is local ip
        second_ip = vif_dic.get('1', {}).get('ip', None)
        vm_host_ip = self.vnet_driver.get_host_manage_interface_infor()['IP']
        # TODO: sync disk size
        # for disk in disk_info:
        #     disk_size += virt_driver.get_disk_size(inst_name, disk)
        os_info = self.virt_driver.get_os_type(inst_name, short_name=False)

        sync_data = {"cpu_cores": cpu_cores,
                     "memory_size": int(memory_size),
                     "disk_num": int(disk_num),
                     "first_ip": first_ip,
                     "second_ip": second_ip,
                     "vm_host_ip": vm_host_ip,
                     "os_info": os_info
                     }
        try:
            ret = self.db_driver.update(sn=sn, data=sync_data)
        except Exception as error:
            log.debug("Exception raise when update vm database: %s", error)
            ret = False
        if not ret:
            log.warn("Update database information with ret: [%s], data: %s", ret, sync_data)

        return ret

    def update_ip_infor_to_database(self, inst_name, vif_index=None, ip=None, host_ip=None):
        """
        As the IP for xenserver'VM is not accessable when it is down, so update it with user's input
        :param inst_name:
        :param vif_index: vif index
        :param ip: the IP on vif
        :param host_ip: Host server IP
        :return:
        """
        log.info("Update [%s] IP information [%s, %s] to database.", inst_name, vif_index, ip)

        sync_data = {}
        if host_ip:
            sync_data['vm_host_ip'] = host_ip
        if vif_index == "0":
            sync_data["first_ip"] = ip
        elif vif_index == "1":
            sync_data["second_ip"] = ip
        else:
            log.warn("Database only record the first and second IP for VM.")

        if not sync_data:
            return True

        try:
            #  json_data = json.dumps(sync_data)
            ret = self.db_driver.update(hostname=inst_name, data=sync_data)
        except Exception as error:
            log.exception("update IP information raise error: %s", error)
            ret = False
        if not ret:
            log.warn("Update IP information to database with ret: [%s], data: %s", ret, sync_data)

        return ret

    def delete_ip_info_from_database(self, inst_name, vif_index):
        """
        delete the ip in database
        :param inst_name:
        :param vif_index:
        :return:
        """
        log.info("Delete vif [%s] IP information from database.", vif_index)

        sync_data = {}
        if vif_index == "0":
            sync_data["first_ip"] = None
        elif vif_index == "1":
            sync_data["second_ip"] = None
        else:
            log.info("No IP with vif index [%s] in database, return.", vif_index)
            return True

        try:
            ret = self.db_driver.update(hostname=inst_name, json_data=sync_data)
        except Exception as error:
            log.warn("Delete ip information raise error: %s", error)
            ret = False
        if not ret:
            log.warn("Delete IP information from database with ret: [%s], data: %s", ret, sync_data)

        return ret

    def update_memory_to_database(self, inst_name):
        """
        :param inst_name:
        :return:
        """
        log.info("Update [%s] memory information to database.", inst_name)

        vm_record = self.virt_driver.get_vm_record(inst_name=inst_name)
        if not vm_record:
            return False
        memory_size = vm_record['memory_target']
        sn = vm_record['uuid']

        return self.db_driver.update(sn=sn, data={"memory_size": memory_size})

    def update_vcpu_to_database(self, inst_name):
        """
        :param inst_name:
        :return:
        """
        log.info("Update [%s] VCPU information to database.", inst_name)

        vm_record = self.virt_driver.get_vm_record(inst_name=inst_name)
        if not vm_record:
            return False
        cpu_cores = vm_record['VCPUs_live']
        sn = vm_record['uuid']

        return self.db_driver.update(sn=sn, data={"cpu_cores": cpu_cores})


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))
    dom= VirtHostDomain(host_name=options.host, user=options.user, passwd=options.passwd)
    print dom.get_all_disk_info(inst_name="test2")
    print dom.get_all_vifs_info(inst_name="test2")
    print dom.get_default_device()
    print dom.get_all_vifs_info("test2")
    print dom.get_default_device()
    print dom.get_host_all_storage_info()
    print dom.print_server_hardware_info()
    print dom.update_database_info(inst_name="test1")
