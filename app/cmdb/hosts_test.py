#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: hosts_test.py
 Author: longhui
 Created Time: 2018-03-22 10:50:42
'''
import unittest

from app.cmdb.hosts import VirtualHost
from lib.Log.log import log


class VirtualHostTestCase(unittest.TestCase):

    def setUp(self):
        self.virthost = VirtualHost()
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
        self.assertListEqual(self.virthost.query(id=-1), [], "query id=-1 should be []")
        self.assertListEqual(self.virthost.query(sn=self.testdata['sn'],
                                                 hostname=self.testdata['hostname']),
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

    def test_c_delete(self):
        log.info("Test test_c_delete")
        data = self.virthost.query(sn=self.testdata['sn'], hostname=self.testdata['hostname'])
        pk = data[0]['id']
        self.assertTrue(self.virthost.delete(id=pk), "shoud delete successfully")
        self.assertListEqual(self.virthost.query(id=pk), [], "query with new pk after delete should be []")
        self.assertEqual(self.virthost.respond_data_count, 0, "after delete record should be 0")

        self.assertListEqual(self.virthost.query(sn=self.testdata['sn'],
                                                 hostname=self.testdata['hostname']),
                                                 [], "query should be []")
        self.assertEqual(self.virthost.query(sn=self.testdata['sn']), [],
                         "query with sn should be []")
        self.assertEqual(self.virthost.query(hostname=self.testdata['hostname']), [],
                         "query with hostname should be []")


if __name__ == "__main__":
    unittest.main()
