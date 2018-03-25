#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: hosts_test.py
 Author: longhui
 Created Time: 2018-03-22 10:50:42
'''
import unittest

from app.cmdb.hosts import VirtualHostDriver, HostDriver
from lib.Log.log import log


class VirtualHostTestCase(unittest.TestCase):

    def setUp(self):
        self.virthost = VirtualHostDriver()
        self.testdata = {
                        "sn": "virtualVmTestCase",
                        "cpu_cores": 1,
                        "memory_size": 4,
                        "disk_size": 20,
                        "disk_num": 1,
                        "hostname": "virtual Vm Test Case",
                        "first_ip": "192.168.1.20"
                        }

    def tearDown(self):
        self.virthost.close()

    def test_a_quiry(self):
        log.info("Test test_a_quiry")
        self.assertNotEqual(self.virthost.query(), [], "query with no params should not be []")
        print self.virthost.respond_data_count
        self.assertNotEqual(self.virthost.respond_data_count, 0, "query with no params return record counts should not be 0")
        self.assertListEqual(self.virthost.query(id=-1), [], "query id=-1 should be []")
        self.assertListEqual(self.virthost.query(sn=self.testdata['sn'], hostname=self.testdata['hostname']),
                             [], "query should be []")
        self.assertEqual(self.virthost.query(sn=self.testdata['sn']), [],
                         "query with sn should be []")
        self.assertEqual(self.virthost.query(hostname=self.testdata['hostname']), [],
                         "query with hostname should be []")

    def test_b_create(self):
        log.info("Test test_b_create")
        self.assertTrue(self.virthost.create(**self.testdata), "create should be true")

        data = self.virthost.query(sn=self.testdata['sn'], hostname=self.testdata['hostname'])
        self.assertEqual(self.virthost.respond_data_count, 1, "data count shoud be 1")
        pk = data[0]['id']
        self.assertNotEqual(data, [], "query should not be []")
        self.assertEqual(self.virthost.is_respond_error, False, "shoud be no error")

        self.assertNotEqual(self.virthost.query(sn=self.testdata['sn']), [],
                            "query with sn should not be []")
        self.assertNotEqual(self.virthost.query(hostname=self.testdata['hostname']), [],
                            "query with hostname should not be []")
        self.assertEqual(self.virthost.respond_data_count, 1, "data count shoud be 1")

        self.assertNotEqual(self.virthost.query(id=pk), [], "query with new pk should not be []")

    def test_c_update(self):
        log.info("Test test_c_update")
        self.assertFalse(self.virthost.update(id=-1, data={}), "update id=-1 record should return False")
        self.assertFalse(self.virthost.update(id=1), "update data is None should return False")
        self.assertTrue(self.virthost.update(hostname=self.testdata['hostname'], data={"hostname": "test_c_update",
                                                                                       "first_ip": "10.101.10.10"}),
                        "Update should return True")

    def test_d_delete(self):
        log.info("Test test_d_delete")
        self.assertTrue(self.virthost.update(sn=self.testdata['sn'], data={'hostname': self.testdata['hostname']}))
        data = self.virthost.query(sn=self.testdata['sn'], hostname=self.testdata['hostname'])
        self.assertNotEqual(data, [], "should not be []")
        pk = data[0]['id']
        self.assertFalse(self.virthost.delete(), "Delete without params should not successfully")
        self.assertTrue(self.virthost.delete(id=pk), "should delete successfully")
        self.assertListEqual(self.virthost.query(id=pk), [], "query with new pk after delete should be []")
        self.assertEqual(self.virthost.respond_data_count, 0, "after delete record should be 0")

        self.assertListEqual(self.virthost.query(sn=self.testdata['sn'], hostname=self.testdata['hostname']),
                             [], "query should be []")
        self.assertEqual(self.virthost.query(sn=self.testdata['sn']), [],
                         "query with sn should be []")
        self.assertEqual(self.virthost.query(hostname=self.testdata['hostname']), [],
                         "query with hostname should be []")


class HostTestCase(VirtualHostTestCase):

    def setUp(self):
        log.info("Setup in HostTestCase")
        self.virthost = HostDriver()
        self.testdata = {
                        "sn": "hostDriverTestCase",
                        "cpu_cores": 4,
                        "memory_size": 4,
                        "disk_size": 20,
                        "disk_num": 2,
                        "hostname": "Physical Host Test Case",
                        "first_ip": "192.168.11.11"
                        }

    def tearDown(self):
        log.info("tearDown in HostTestCase")
        self.virthost.close()


if __name__ == "__main__":
    unittest.main()
