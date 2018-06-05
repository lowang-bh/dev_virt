#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: xml_utils.py
 Author: longhui
 Created Time: 2018-05-17 14:15:00
"""
from lxml import etree
from lib.Log.log import log
from xml.etree.ElementTree import ElementTree

def validate(schemaFile, xmlFile):
    try:
        with open(schemaFile) as f:
            schemaDoc = etree.parse(f)
            schema = etree.XMLSchema(schemaDoc)

        with open(xmlFile) as f:
            xmlDoc = etree.parse(f)
        schema.assert_(xmlDoc)
    except Exception as e:
        log.exception(str(e))
        return False

    return True


def parse_xml(xml_file):
    """
    parse the example xml
    :param xml_file:
    :return:[{'passwd': '123456', 'host': '192.168.1.10', 'user': 'root', 'vms': []}]
    """
    tree = ElementTree()
    tree.parse(xml_file)
    servers = tree.findall('SERVER')
    server_list=[]
    for server in servers:
        #print type(server), server.get('user'), server.get('serverIp'), server.get('host'), type(server.attrib)
        host = server.attrib['serverIp']
        user = server.attrib['user']
        passwd = server.attrib['passwd']
        platform = server.get("platform")
        server_dict = {'host':host, 'user':user, 'passwd':passwd, 'platform': platform, 'vms':[]}
        server_list.append(server_dict)
        for vm in list(server):
            vmname = vm.attrib['vmname']
            vmdict = {'vmname':vmname, 'cpucores':None, 'cpumax':None, 'memory':None, 'minMemory':None, 'maxMemory':None, 'ips':[], 'disks':[]}
            vmdict.update(vm.attrib)
            server_dict['vms'].append(vmdict)
            #parse IP
            ips = vm.findall('IP')
            disks = vm.findall('DISK')
            for ip in ips:
                ipdict = {'vifIndex': None, 'network': None, 'ip': None, 'netmask': None, 'device': None, 'bridge': None}
                ipdict.update(ip.attrib)
                vmdict['ips'].append(ipdict)
            for disk in disks:
                diskdict = {'size':None, 'storage':None}
                diskdict.update(disk.attrib)
                vmdict['disks'].append(diskdict)
            log.debug("ips for vm %s is:%s", vmname,  vmdict['ips'])
            log.debug("disk for vm %s is %s", vmname, vmdict['disks'])

    return server_list


if __name__ == "__main__":
    servers = parse_xml("../../etc/example.xml")
    for server in servers:
        print server
        print type(server), server.get('user'), server.get('serverIp'), server.get('host')
        for key,value in server.items():
            if key != "vms":
                print key, value
            else:
                for vmdic in value:
                    print "-------another VM------"
                    for k,v in vmdic.items():
                        print k, v
