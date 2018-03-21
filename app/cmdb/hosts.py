#!/usr/bin/env python
# -*- coding:UTF-8 -*-

import json
import requests

from lib.Log.log import log
from lib.Db.db_driver import DatabaseDriver
from app.settings import HOSTs_URL


class Host(DatabaseDriver):

    def __init__(self, *args, **kwagrs):
        super(Host, self).__init__(*args, **kwagrs)
        self.url = HOSTs_URL

    def create(self, data):
        """
        write data to db
        :param url:
        :param data:
        :return: True or False
        """
        url = self.url
        db_name = self.db_name(url)

        res = self.session.post(url, data=data)
        log.info("Http return code: %s", res.status_code)
        if res.status_code == requests.codes.created or res.status_code == requests.codes.ok:
            log.info("Create data to database: [%s] successfully.", db_name)
            return True
        else:
            log.error("Create data to database: [%s] failed, please check the log at '/var/log/virt.log'.", db_name)
            #res_dict_data = json.loads(res.content)['data']
            #{"msg":"执行异常！","code":400,"data":{"errors":{"sn":["具有 sn 的 hosts 已存在。"]}}}
            log.debug(res.content)
            return False

    def delete(self, id=None, **kwargs):
        """
        Delete a record from database
        :param pk:
        :return:
        """
        url = self.url if id is None else "/".join(self.url, str(id))
        db_name = self.db_name(url)

        res = self.session.delete(url)
        if self.is_respond_error(json.loads(res.content)):
            log.warn("Delete data from database: [%s] failed.", res.status_code)
            return  False

        return True

    def update(self, id=None, data=None):
        """
        update the data to a record with its primary key is pk
        :param pk:
        :param data:
        :return: True or False
        """
        raise NotImplementedError()

    def query(self, id=None, sn=None, hostname=None):
        """
        query from database
        :param id:
        :return: the record with Dict
        """
        url = self.url
        db_name = self.db_name(url)

        data = {}
        url += "?"
        select_item =[]
        if id:
            data['id'] = id
            select_item.append("id=%s" %id)
        if sn:
            data['sn'] = sn
            select_item.append("sn=%s" %sn)
        if hostname:
            data['hostname'] = hostname
            select_item.append("hostname=%s" %hostname)

        url += "&".join(select_item)
        log.info("Query URL: %s", url)

        res = self.session.get(url)
        if res.status_code == requests.codes.ok:
            log.info("Query from database: [%s] with record [%s] successfully.", db_name, data)
        else:
            log.error("Query from database: [%s] with record [%s] failed, please check the log at '/var/log/virt.log'.", db_name, data)
            log.debug(res.content)

        response_data =  self.respond_data(res.content)
        if not int(response_data.get("count", 0)):
            log.error("No record found with query data: %s.", data)
            return  []
        else:
            return response_data.get('list', [])




class VirtualHost(Host):

    def __init__(self, *args, **kwargs):
        super(VirtualHost, self).__init__(*args, **kwargs)

    def create(self, hostname, sn, cpu_cores, memory_size, disk_size, disk_num, first_ip):
        """
        overwrite the create method in Host for virtual machine
        :param sn: The UUID of the VM
        :param cpu_cores: cpu numbers
        :param memory_size: memory size with unit of GB
        :param disk_size: disk size with unit GB
        :param disk_num: disk number
        :param first_ip: the IP assigned to the VM
        :return:
        """
        post_data = {"machine_type": "虚拟机", "ip_static":True, "os_deploy":True}
        post_data.setdefault('hostname', hostname)
        post_data.setdefault('sn', sn)
        post_data.setdefault('cpu_cores', cpu_cores)
        post_data.setdefault('memory_size', memory_size)
        post_data.setdefault('disk_size', disk_size)
        post_data.setdefault('disk_num', disk_num)
        post_data.setdefault('first_ip', first_ip)

        url = self.url
        db_name = self.db_name(url)

        res = self.session.post(url, data=post_data)
        log.info("Http return code: %s", res.status_code)
        if res.status_code == requests.codes.created or res.status_code == requests.codes.ok:
            log.info("Create data to database: [%s] successfully.", db_name)
            return True
        else:
            log.error("Create data to database: [%s] failed, please check the log at '/var/log/virt.log'.", db_name)
            #res_dict_data = json.loads(res.content)['data']
            #{"msg":"执行异常！","code":400,"data":{"errors":{"sn":["具有 sn 的 hosts 已存在。"]}}}
            log.debug(res.content)
            return False

if __name__ == "__main__":
    virhost= VirtualHost()
    testdata = {
        "sn": "virtual vm 1",
        "cpu_cores": 1,
        "memory_size": 4,
        "disk_size": 20,
        "disk_num": 1,
        "hostname": "virtualVm1",
        "first_ip":"192.168.1.2"
        }
    if  not virhost:
        print "Host init failed"
        exit(1)

    print virhost.query(sn="virtual vm 1")


    #print virhost.create(**testdata)
