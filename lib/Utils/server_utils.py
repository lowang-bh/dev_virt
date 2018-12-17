#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: server_utils.py
 Author: longhui
 Created Time: 2018-03-13 18:41:44
 Descriptions: API to get information about the Server/Host
'''
from lib.Db.db_factory import DbFactory
from lib.Log.log import log
from lib.Utils.network_utils import IpCheck, is_IP_pingable
from lib.Val.virt_factory import VirtFactory


class ServerDomain(object):

    def __init__(self, host_name=None, user="root", passwd=""):
        self.virt_driver = VirtFactory.get_virt_driver(host_name, user, passwd)
        self.vnet_driver = VirtFactory.get_vnet_driver(host_name, user, passwd)
        self.db_driver = DbFactory.get_db_driver("Host")

    def __nonzero__(self):
        if self.virt_driver and self.vnet_driver and self.db_driver:
            return True
        else:
            if not self.virt_driver or not self.vnet_driver:
                log.error("Can not connect to virtual driver.")
            if not self.db_driver:
                log.error("Can not connect to DB driver.")
            return False

    @property
    def server_name(self):
        """
        The name label of the server, in Xen server, it is same as the name in Xen center.
        if the Hypervisor is KVM, return hostname
        :return:
        """
        name_info = self.virt_driver.get_host_name()
        return name_info[0]

    def print_server_hardware_info(self):
        """
        Display server hardware and platform info
        """
        log.info("General hardware and software information:")

        log.info("\nHost Manufacturer informations:")
        platform_info = self.virt_driver.get_host_plat_info()
        log.info("\tManufacturer: %s", platform_info.get('vendor_name'))
        log.info("\tModel: %s", platform_info.get('product_name'))
        log.info("\tSerial Number: %s", platform_info.get('serial_number'))
        log.info("\tSoftware Version: %s", self.virt_driver.get_host_sw_ver(short_name=False))

        log.info("\nHost CPU informations:")
        cpu_info = self.virt_driver.get_host_cpu_info()
        log.info("\tProcessor Model: %s", cpu_info.get("cpu_model"))
        log.info("\tProcessor Sockets: %s", cpu_info.get("cpu_sockets", 0))
        log.info("\tCores per Socket: %s", cpu_info.get("cores_per_socket", 0))
        log.info("\tThreads per Core: %s", cpu_info.get("thread_per_core", 1))
        log.info("\tLogical Processors: %s", cpu_info.get("cpu_cores"))
        log.info("\tProcessor Speed: %s MHz", cpu_info.get("cpu_speed"))

        log.info("\nHost Memory informations:")
        memory_info = self.virt_driver.get_host_mem_info()
        log.info("\tMemory total: %s GB", memory_info.get("size_total"))
        log.info("\tMemory used: %s GB", memory_info.get("size_used"))
        log.info("\tMemory free: %s GB", memory_info.get("size_free"))

        log.info("\nHost Default Storage informations:")
        storage_info = self.virt_driver.get_host_storage_info()
        log.info("\tStorage Size: %s GB", storage_info.get('size_total', 0))
        log.info("\tStorage Used: %s GB", storage_info.get('size_used', 0))
        log.info("\tStorage Free: %s GB", storage_info.get('size_free', 0))

    def print_all_interface(self):
        """
        :return:
        """
        log.info("All PIFs information with index number and MAC, IP:")

        all_pifs = self.vnet_driver.get_all_devices()
        for pif_index, pif_name in enumerate(sorted(all_pifs)):
            pif_infor = self.vnet_driver.get_device_infor(device_name=pif_name)
            bridge_name = self.vnet_driver.get_bridge_name(device_name=pif_name)
            mac = pif_infor.get('MAC')
            ip = pif_infor.get('IP')
            ip = ip if ip else None
            log.info("%s\t%-15s\tMAC: %s, IP: %15s, Bridge: %s", pif_index, pif_name, mac, ip, bridge_name)

        return True

    def print_bond_inforation(self):
        """
        :return:
        """
        log.info("All bond information with index number and MAC, IP:")
        all_bondinfo = self.vnet_driver.get_host_bond_info()
        for bond_name in sorted(all_bondinfo.keys()):
            log.info("\tBond Device: %s", bond_name)
            for device_infor in all_bondinfo[bond_name]:
                log.info("%s\tMAC: %s, IP: %s", device_infor['device'], device_infor.get('MAC'), device_infor.get('IP'))
        return True

    def print_all_vms(self):
        """
        :return:
        """
        log.info("All VMs in server: %s", self.server_name)
        vms = self.virt_driver.get_vm_list()
        log.info(vms)
        return True

    def get_host_all_storage_info(self):
        """
        :return:
        """
        storage_info = {}
        sr_list = self.virt_driver.get_host_all_storages()
        for sr in sr_list:
            size = self.virt_driver.get_host_storage_info(storage_name=sr)
            storage_info.setdefault(sr, [size['size_total'], size['size_free']])

        return storage_info

    def get_default_device(self):
        """
        get the host's default network/Interface which has configured an IP;
        :return: Interface name on host, or None
        """
        log.info("Get the host manage interface as the default device.")

        device_info = self.vnet_driver.get_host_manage_interface_infor()
        device_name = device_info.get('device', None)
        if device_name:
            return device_name

        log.info("Get the host default network with IP configured.")
        devices = self.vnet_driver.get_all_devices()
        for device_name in devices:
            # 'IP': '' or an ip,
            device_info = self.vnet_driver.get_device_infor(device_name=device_name)
            ipstr = device_info.get('IP', '')
            if ipstr:
                return device_name
        else:
            log.error("No device found with an IP configured.")
            return None

    def get_all_devices(self):
        """
        :return: all the physical interface or bridge in server
        """
        return self.vnet_driver.get_all_devices()

    def get_network_list(self):
        """
        in KVM, network return kvm network def, bridge list return raw bridge name
        :return:
        """
        return self.vnet_driver.get_network_list()

    def get_bridge_list(self):
        """
        in XEN, network list and bridge list return all bridge name
        :return:
        """
        return self.vnet_driver.get_bridge_list()

    def get_vm_list(self):
        """
        :return:
        """
        return self.virt_driver.get_vm_list()

    def get_templates_list(self):
        """
        :return:
        """
        return self.virt_driver.get_templates_list()

    def get_max_free_size_storage(self):
        """
        get the default storage repository which has the largest volume for user
        :return: the storage name
        """
        log.info("Get the host default storage name which has the largest free volume.")

        all_sr = self.virt_driver.get_host_all_storages()
        max_volume, target_sr = 0, None
        for sr in all_sr:
            storage_dict = self.virt_driver.get_host_storage_info(storage_name=sr)
            temp = int(storage_dict.get('size_free', 0))
            if temp > max_volume:
                max_volume, target_sr = temp, sr

        log.info("The default storage is '%s' with volume %s GB.", target_sr, max_volume)
        return target_sr

    def check_ip_used(self, ip):
        """
        check the ip from database
        :param ip:
        :return:
        """
        query_data = self.db_driver.query()
        ip_list = [d["first_ip"] for d in query_data]
        ip_list.extend([d['second_ip'] for d in query_data])

        if ip in ip_list:
            return True
        else:
            return False

    def is_IP_available(self, vif_ip=None, vif_netmask=None, device=None, network=None, bridge=None):
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
                device_info = self.vnet_driver.get_device_infor(device_name=device)
                dest_metmask = device_info["netmask"]
                dest_gateway = device_info['gateway']
            except KeyError as error:
                log.exception(str(error))
        elif network is not None or bridge is not None:
            # TODO: need to add API to get network infor accroding to network or bridge
            pass

        if vif_netmask:
            if dest_metmask and dest_metmask != vif_netmask:
                log.error("Netmask [%s] is not corresponding with the target network.", vif_netmask)
                return False
        else:  # get the netmask on device as the default one
            vif_netmask = dest_metmask
        log.debug("VIF IP is: %s, netmask is: %s", vif_ip, vif_netmask)
        if not vif_netmask:  # No default netmask and no given
            log.warn("No netmask given, the default one is '255.255.255.0'.")
        else:
            vif_gateway = dest_gateway if dest_gateway else None
            if not IpCheck.is_valid_ipv4_parameter(vif_ip, vif_netmask, gateway=vif_gateway):
                return False

        #  First check it from database
        if self.check_ip_used(vif_ip):
            log.error("Ip address [%s] already in used.(Check from database).", vif_ip)
            return False
        # This ping test take a second, put it at last.
        if is_IP_pingable(vif_ip):
            log.error("Ipaddress [%s] is already be used(Ping test).", vif_ip)
            return False

        return True

    def create_database_info(self):
        """
        :return:
        """
        log.info("Start to create [%s] information to databse.", self.server_name)

        hostname = self.server_name
        if self.db_driver.query(hostname=hostname):
            log.info("The hostname [%s] has exist in database.", hostname)
            return True

        cpu_cores = self.virt_driver.get_host_cpu_info().get('cpu_cores')
        sn = self.virt_driver.get_host_plat_info().get('serial_number')
        memory_size = self.virt_driver.get_host_mem_info().get('size_total')

        disk_num = len(filter(lambda x: int(x[0]) > 10, self.get_host_all_storage_info().values()))
        default_storage = self.virt_driver.get_host_storage_info()  # only write the system disk size
        disk_size = default_storage.get('size_total', 0)

        first_ip = self.vnet_driver.get_host_manage_interface_infor().get('IP')

        ret = self.db_driver.create(hostname=hostname, sn=sn, cpu_cores=cpu_cores, memory_size=int(memory_size),
                                    disk_size=int(disk_size), disk_num=disk_num, first_ip=first_ip)
        if ret:
            log.info("Create server [%s] record to database successfully.", hostname)
        else:
            log.error("Create server [%s] record to database failed.", hostname)

        return ret

    def delete_database_info(self):
        """
        delete from database with this server
        :return:
        """
        log.info("Start to delete [%s] information from database.", self.server_name)

        return self.db_driver.delete(hostname=self.server_name)

    def update_database_info(self):
        """
        This function is used to sync server information, include:cpu_cores, memory_size, disk_num
        :return:
        """
        server_name = self.server_name
        log.info("Start to update [%s] information to database.", server_name)

        sn = self.virt_driver.get_host_plat_info().get('serial_number')
        if not self.db_driver.query(sn=sn, hostname=server_name):
            log.info("No record found with server name [%s], don't update.", server_name)
            return True

        cpu_cores = self.virt_driver.get_host_cpu_info().get('cpu_cores')
        memory_info = self.virt_driver.get_host_mem_info()
        memory_size = memory_info.get('size_total')
        free_memory = memory_info.get('size_free')

        storage_info = self.get_host_all_storage_info()
        disk_size, disk_free, disk_num = 0, 0, 0
        # disk_num = len(filter(lambda x: int(x[0]) > 10, self.get_host_all_storage_info().values()))
        for sr, disk in storage_info.iteritems():
            if int(disk[0]) > 10:
                disk_num += 1
                disk_size += disk[0]
                disk_free += disk[1]
        # default_storage = self.virt_driver.get_host_storage_info()  # only write the system disk size
        # disk_size = default_storage.get('size_total')
        # disk_free = default_storage.get('size_free')

        first_ip = self.vnet_driver.get_host_manage_interface_infor().get('IP')
        os_info = self.virt_driver.get_host_os()

        sync_data = {"cpu_cores": cpu_cores,
                     "memory_size": int(memory_size),
                     "free_memory": int(free_memory),
                     "disk_num": int(disk_num),
                     "disk_size": int(disk_size),
                     "disk_free": int(disk_free),
                     "first_ip": first_ip,
                     'vm_host_ip': first_ip,  # as for server, take the manage ip as vm host ip
                     'os_info': os_info,
                     'power_state': "ON"
                     }
        comment = "Update server by virtualization API with data: %s" % sync_data
        sync_data['comment'] = comment
        try:
            ret = self.db_driver.update(sn=sn, hostname=server_name, data=sync_data)
        except Exception as error:
            log.exception("Exception raise when update server database: %s", error)
            ret = False
        if not ret:
            log.warn("Update server db information return ret: [%s], data: %s", ret, sync_data['comment'])

        return ret

    def update_memory_to_database(self):
        """
        sync server's memory to cmdb
        :return: true or false
        """
        server_name = self.server_name
        log.info("Start to update [%s] memory information to database.", server_name)

        sn = self.virt_driver.get_host_plat_info().get('serial_number')
        if not self.db_driver.query(sn=sn, hostname=server_name):
            log.info("No record found with server name [%s], don't update.", server_name)
            return True

        memory_info = self.virt_driver.get_host_mem_info()
        memory_size = memory_info.get('size_total')
        free_memory = memory_info.get('size_free')

        sync_data = {
            "memory_size": int(memory_size),
            "free_memory": int(free_memory)
            }

        comment = "Update server memory by virtualization API with data: %s" % sync_data
        sync_data['comment'] = comment

        try:
            ret = self.db_driver.update(sn=sn, hostname=server_name, data=sync_data)
        except Exception as error:
            log.exception("Exception raise when update server memory to cmdb: %s", error)
            ret = False
        if not ret:
            log.warn("Update server memory information return ret: [%s], data: %s", ret, sync_data['comment'])

        return ret

    def update_storage_to_database(self):
        """
        sync server's storage info to cmdb
        :return: true or false
        """

        server_name = self.server_name
        log.info("Start to update [%s] storage information to database.", server_name)

        sn = self.virt_driver.get_host_plat_info().get('serial_number')
        if not self.db_driver.query(sn=sn, hostname=server_name):
            log.info("No record found with server name [%s], don't update.", server_name)
            return True

        storage_info = self.get_host_all_storage_info()
        disk_size, disk_free, disk_num = 0, 0, 0
        for sr, disk in storage_info.iteritems():
            if int(disk[0]) > 10:
                disk_num += 1
                disk_size += disk[0]
                disk_free += disk[1]

        sync_data = {
            "disk_num": int(disk_num),
            "disk_size": int(disk_size),
            "disk_free": int(disk_free)
            }

        comment = "Update server storage by virtualization API with data: %s" % sync_data
        sync_data['comment'] = comment

        try:
            ret = self.db_driver.update(sn=sn, hostname=server_name, data=sync_data)
        except Exception as error:
            log.exception("Exception raise when update server storage to cmdb: %s", error)
            ret = False
        if not ret:
            log.warn("Update server storage information return ret: [%s], data: %s", ret, sync_data['comment'])

        return ret


if __name__ == "__main__":
    host = ServerDomain(host_name="192.168.1.2", user="root", passwd="123456")
    storage = host.get_host_all_storage_info()
    for k, v in storage.iteritems():
        print k, "\t\t", v

    print host.virt_driver.get_host_all_storages()

    print host.get_max_free_size_storage()

    print host.get_default_device()
    print host.print_server_hardware_info()
    print host.check_ip_used("192.168.1.100")
    print host.create_database_info()
    print host.update_database_info()
