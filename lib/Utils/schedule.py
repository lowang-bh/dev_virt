#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: lib/Utils/schedule.py
 Author: longhui
 Created Time: 2019-04-24 16:13:39
"""

import operator
import platform
import re
import subprocess

from ipaddress import ip_network

import lib.Db.mysqldb as mysqldb
from lib.Log.log import log
from lib.Utils.constans import Libvirtd_Pass, Libvirtd_User, DISK_POOL, MEMORY_OVERCOMMIT_FRACTION
from lib.Utils.network_utils import is_IP_pingable
from lib.Utils.signal_utils import TimeoutError
from lib.Val.kvm.virt_driver_kvm import QemuVirtDriver
from lib.Val.kvm.vnet_driver_kvm import QemuVnetDriver


def generate_vmname_key(role, cluster):
    """
    :param role: role name
    :param cluster: cluster name
    :return: 
    """
    if role == "jenkins":
        key = "sa-jenkins-k8s"
    elif role == "etcd":
        key = "sa-etcd-" + cluster
    elif cluster in ["test", "xyz"]: # test,xyz cluster name rule
        key = "sa-k8s-" + cluster
    else:  # other roles: node, master, ingress, etc
        key = "sa-k8s-" + role
    return key


def fetch_hosts_info():
    """
    return kvm hosts ip list
    """

    try:
        with mysqldb.MysqlDB() as dbconn:
            hosts = dbconn.get_kvm_host_list()
    except TimeoutError:
        log.error("Connect to mysql db timeout.")
        return []

    return hosts


def fetch_used_ips_from_db():
    """
    :return: ip list has used
    """
    try:
        with mysqldb.MysqlDB() as dbconn:
            firstIPs = dbconn.get_firt_ip_list()
            secondIps = dbconn.get_second_ip_list()
            vips = dbconn.get_vip_list()
    except TimeoutError:
        log.error("Connect to mysql db timeout.")
        exit(1)

    return firstIPs + secondIps + vips


def fetch_vm_name_list(key):
    """
    return kvm vm list with role in cluster
    """
    try:
        with mysqldb.MysqlDB() as dbconn:
            vmlist = dbconn.get_kvm_vmname_list(key)
    except TimeoutError:
        log.error("Connect to mysql db timeout.")
        exit(1)

    return vmlist


def find_default_available_ip(server_ip, template_name):
    """
    use the template's network to find the default ip for new vm
    :param server_ip: host ip
    :param template_name: template name for new vm
    :return: 
    """

    target_network, target_netmask = None, None
    vnetDeriver = QemuVnetDriver(server_ip, Libvirtd_User, Libvirtd_Pass)
    if vnetDeriver:
        br_name = vnetDeriver.get_vif_bridge_name(template_name, 0)
        device_info = vnetDeriver.get_bridge_info(bridge_name=br_name)
        target_network = device_info.get("IP", None)
        target_netmask = device_info.get("netmask", None)

    if not target_network:
        log.error("Can not find the target network for new vm.")
        return None
    if not target_netmask:
        target_netmask = "24"

    ip_address_netmask = ip_network(unicode(target_network + "/" + target_netmask), strict=False)
    avaiable_hosts = [str(ip) for ip in ip_address_netmask.hosts()]
    # just to fetch ip info when find default ip
    used_ips = fetch_used_ips_from_db()

    if platform.system() == "Linux":
        cmd = "nmap -v -sn -n %s -oG - | awk '/Status: Down/{print $2}'" % ip_address_netmask
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        pout, perr = p.communicate()
        if perr:
            log.error("subprocess execute return eror: %s", perr)
            return None

        for ip in pout.splitlines():
            if (ip not in used_ips) and (ip in avaiable_hosts):
                return ip
    elif platform.system() == "Darwin":
        for ip in avaiable_hosts:
            if ip in used_ips:
                continue
            if is_IP_pingable(ip):
                continue
            return ip
    else:
        for ip in avaiable_hosts:
            if ip not in used_ips:
                return ip

    log.warn("Can not find a available ip for new vm")
    return None


def get_server_infors(hosts):
    """
    logic-free-mem: server-total-phyMem * scale - allocated-to-vm
    logic-free-disk: disk-pool-phySize - allocated-to-vm
    :param hosts: a server list with its item is server ip
    :return: a dict with server ip as key, and value is 
    [logic-free-mem-without-overCommit, physic-free-mem, logic-free-mem-overCommit, physic-free-disk, logic-free-disk]
    """
    server_infors = {}
    for host in hosts:
        info_list = [0, 0, 0, 0, 0]
        virtDeriver = QemuVirtDriver(host, Libvirtd_User, Libvirtd_Pass)
        if not virtDeriver:
            continue

        pysical_mem_info = virtDeriver.get_host_phymem()
        pysical_total = pysical_mem_info.get("size_total", 0)
        logic_allocted = virtDeriver.get_all_allocaled_mem()
        info_list[0] = float("%.3f" % (pysical_total - logic_allocted))
        info_list[1] = pysical_mem_info.get("size_free", 0)
        info_list[2] = float("%.3f" % (pysical_total * MEMORY_OVERCOMMIT_FRACTION - logic_allocted))
        info_list[3], info_list[4] = virtDeriver.get_storage_pool_free_size(DISK_POOL)
        server_infors[host] = info_list

    return server_infors


def find_default_server(hosts, role, config_dict):
    """
    :param hosts: server's ip list
    :return: a default server's Ip
    """
    server_infors = get_server_infors(hosts)
    # each item is tuple (server_ip,  [logicFreeNoOverCommit, physic-free-mem, logic-free-mem, physic-free-disk, logic-free-disk])
    sorted_servers = sorted(server_infors.iteritems(), key=lambda (k, v): operator.itemgetter(0, 1, 2)(v), reverse=True)
    for item in sorted_servers:
        log.debug("%s", item)

    for ip, info in sorted_servers:
        # find a server's physical memory at least has 10GB free memory to start a new vm,
        # and logic free memory with over commit fit the logic memory size in new vm,
        # and the disk pool has at least 100G free 
        if (info[1] > 10) and (info[2] - config_dict[role]['memory'] > 0) and (info[3] > 100):
            default_server = ip
            break
    else:
        log.error("No server is available for the new vm, please confirm it.")
        return None

    log.info("Schedual to server: %s", default_server)

    return default_server


def generate_default_vm_name(role, cluster, default_server):
    """
    :return: a default vm name
    """
    vm_key = generate_vmname_key(role, cluster)
    vmlist = fetch_vm_name_list(vm_key)
    nums_list = [1] # default 1 in case of no such vm
    myreg = re.compile(r'%s([0-9]+)' % vm_key)
    for vm_name in vmlist:
        res = myreg.search(vm_name)
        if res:
            nums_list.append(int(res.group(1)))
    upper = max(nums_list)
    for i in xrange(1, upper + 1):
        if i not in nums_list:
            default_vmname = "".join(["kvm", str.split(default_server, ".")[-1], "-", vm_key, str(i)])
            break
    else:
        default_vmname = "".join(["kvm", str.split(default_server, ".")[-1], "-", vm_key, str(i + 1)])

    return default_vmname


def get_available_vm_info(role, cluster, config_dict):
    """
    return host_ip, new_vm_name and new_ip for a new vm
    """
    hosts = fetch_hosts_info()
    if not hosts:
        log.error("Can not get server info from cmdb...")
        return None, None, None

    log.info("Start to calculate default server...")
    default_server = find_default_server(hosts, role, config_dict)
    if not default_server:
        log.error("Failed to find default server.")
        return None, None, None

    # get the default vm name
    default_vmname = generate_default_vm_name(role, cluster, default_server)
    default_ip = find_default_available_ip(default_server, config_dict[role]["template"])

    return default_server, default_vmname, default_ip


if __name__ == "__main__":
    hosts = fetch_hosts_info()
    print(hosts)

    # print(get_server_infors(hosts))
    from lib.Utils.constans import template_dict


    print get_available_vm_info("etcd", "test", template_dict)
