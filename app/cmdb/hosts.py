#!/usr/bin/env python
# -*- coding:UTF-8 -*-

import requests

from lib.Log.log import log
from app.cmdb.host_driver import HostDbDriver
from app.cmdb.settings import HOSTs_URL


class HostDriver(HostDbDriver):

    def __init__(self, *args, **kwagrs):
        super(HostDriver, self).__init__(*args, **kwagrs)
        self.url = HOSTs_URL

    def create(self, **kwargs):
        """
        write data to db
        :return: True or False
        """
        url = self.url
        db_name = self.db_name(url)
        data = kwargs
        data.setdefault("machine_type", "物理机")

        log.debug("Create url: %s, with data:%s", url, data)
        self.resp = self.session.post(url, data=data)
        log.info("Http return code: %s", self.resp.status_code)
        if self.resp.status_code == requests.codes.created or self.resp.status_code == requests.codes.ok:
            log.info("Create data to database: [%s] successfully.", db_name)
            return True
        else:
            log.error("Create data to database: [%s] failed, please check the log at '/var/log/virt.log'.", db_name)
            # {"msg":"执行异常！","code":400,"data":{"errors":{"sn":["具有 sn 的 hosts 已存在。"]}}}
            log.debug(self.resp.content)
            return False

    def delete(self, id=None, sn=None, hostname=None):
        """
        Delete a record from database
        :param id: pk
        :param sn:
        :param hostname:
        :return:
        """
        if id is None and sn is None and hostname is None:
            log.error("Delete record from DB need an ID, a hostname or a SN to identify which record will be deleted.")
            return False

        if id is None:
            query_data = self.query(sn=sn, hostname=hostname)
            if not query_data:
                log.info("No record found to delete with sn:%s and hostname:%s.", sn, hostname)
                return True
            id_list = [record['id'] for record in query_data]
        else:
            id_list = [id]

        for id in id_list:
            url = self.url + str(id)
            db_name = self.db_name(url)
            log.debug("Delete url: %s", url)

            self.resp = self.session.delete(url)
            if self.resp.status_code == requests.codes.no_content:
                log.info("Delete data from database [%s] successfully.", db_name)
            elif self.resp.status_code == requests.codes.not_found:
                log.warn("Not found the record when delete from [%s]: 404", db_name)
            elif self.is_respond_error:
                log.warn("Delete data from database: [%s] failed, return code: %s.", db_name, self.resp.status_code)
                return False

        return True

    def update(self, id=None, sn=None, hostname=None, data=None):
        """
        update the data to a record with its primary key is id, id/sn/hostname should not be changed
        :param id: PK
        :param sn: UUID for VM, or Serial No. of Physical host
        :param hostname: VM name or host name for physical host
        :param data: Dict data
        :return: True or False
        """
        if id is None and sn is None and hostname is None:
            log.error("Update to DB need an ID, a hostname or a SN to identify which record will be updated.")
            return False
        if not isinstance(data, dict):
            log.error("Data should be a dict.")
            return  False

        query_list = self.query(id=id, sn=sn, hostname=hostname)
        if not query_list:
            log.error("No record found with ID:%s, hostname:%s, sn:%s", id, hostname, sn)
            return False

        modified = query_list[0]['modified']
        record_id = query_list[0]['id']
        data['modified'] = str(modified)

        url = self.url + str(record_id) + "/"  # update url should be endwith "/"
        log.debug("Patch url:%s, data:%s", url, data)
        self.resp = self.session.patch(url, data=data)
        if self.resp.status_code == requests.codes.ok:
            log.info("Update to database successfully.")
            return True
        elif self.is_respond_error:
            log.error("Update failed. Return code: %s", self.resp.status_code)
            log.debug("Error content: %s", self.resp.content)
            return False

        return True

    def query(self, id=None, sn=None, hostname=None):
        """
        query from database
        :param id: PK id
        :param sn: UUID of VM or host
        :param hostname: The name of VM or host
        :return: the record with Dict
        """
        url = self.url
        db_name = self.db_name(url)

        data = {}
        url += "?"
        select_item = []
        if id:
            data['id'] = id
            select_item.append("id=%s" % id)
        if sn:
            data['sn'] = sn
            select_item.append("sn=%s" % sn)
        if hostname:
            data['hostname'] = hostname
            select_item.append("hostname=%s" % hostname)

        url += "&".join(select_item)
        log.debug("Query URL: %s", url)

        self.resp = self.session.get(url)
        if self.resp.status_code == requests.codes.ok:
            log.debug("Query from database: [%s] with record [%s] successfully.", db_name, data)
        else:
            log.error("Query from database: [%s] with record [%s] failed, please check the log at '/var/log/virt.log'.",
                      db_name, data)
            log.debug(self.resp.content)

        if not self.respond_data_count:
            log.warn("No records found with query data: %s.", data)
            return []
        else:
            return self.respond_data_list


class VirtualHostDriver(HostDriver):

    def __init__(self, *args, **kwargs):
        super(VirtualHostDriver, self).__init__(*args, **kwargs)

    def create(self, hostname, sn, cpu_cores, memory_size, disk_size, disk_num, first_ip=None):
        """
        overwrite the create method in Host for virtual machine
        :param hostname: Name of VM
        :param sn: The UUID of the VM
        :param cpu_cores: cpu numbers
        :param memory_size: memory size with unit of GB
        :param disk_size: disk size with unit GB
        :param disk_num: disk number
        :param first_ip: the IP assigned to the VM
        :return:
        """
        post_data = {"machine_type": "虚拟机", "ip_static": True, "os_deploy": True}
        post_data.setdefault('hostname', hostname)
        post_data.setdefault('sn', sn)
        post_data.setdefault('cpu_cores', cpu_cores)
        post_data.setdefault('memory_size', memory_size)
        post_data.setdefault('disk_size', disk_size)
        post_data.setdefault('disk_num', disk_num)
        post_data.setdefault('first_ip', first_ip)

        url = self.url
        db_name = self.db_name(url)

        log.debug("Create virtual host url: %s", url)
        self.resp = self.session.post(url, data=post_data)
        if self.resp.status_code == requests.codes.created or self.resp.status_code == requests.codes.ok:
            log.info("Create data to database: [%s] successfully.", db_name)
            return True
        else:
            log.error("Create data to database: [%s] failed, Http return code: %s, please check the log at "
                      "'/var/log/virt.log'.", db_name, self.resp.status_code)
            log.debug(self.resp.content)
            return False


if __name__ == "__main__":
    virhost = VirtualHostDriver()
    testdata = {
        "sn": "virtual vm 1",
        "cpu_cores": 1,
        "memory_size": 4,
        "disk_size": 20,
        "disk_num": 1,
        "hostname": "virtualVm1",
        "first_ip": "192.168.1.2"
        }
    if not virhost:
        print "Host init failed"
        exit(1)

    print virhost.query(hostname="virtualVm1")
    print virhost.respond_code
    print virhost.respond_msg
    print virhost.respond_data
    print virhost.delete(hostname="virtual Vm Test Case")
    print virhost.delete(sn="hostDriverTestCase")
    print virhost.resp, virhost.resp.content

    with VirtualHostDriver() as test:
        queryDic = test.query(sn=testdata['sn'], hostname=testdata['hostname'])
        if not test.respond_data_count:
            test.create(**testdata)
            queryDic = test.query(sn=testdata['sn'], hostname=testdata['hostname'])
        deleteId = test.respond_data_list[0]['id']
        test.update(id=deleteId, data={"hostname": "hostname", "first_ip": "10.101.10.10"})
        virhost.delete(id=deleteId)
        virhost.delete(id=deleteId)
        test.create(**testdata)
        test.query(sn=testdata['sn'], hostname=testdata['hostname'])
        print test.respond_data_list[0]['id']
