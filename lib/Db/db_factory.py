#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: db_factory.py
 Author: longhui
 Created Time: 2018-03-22 20:33:04
 Descriptions: The factory class for Database crud
'''

import os
from app.cmdb.hosts import HostDriver, VirtualHostDriver
from app.cmdb.fake_db_driver import FakeDBDriver


class DbFactory(object):

    @classmethod
    def get_db_driver(cls, table_class):
        """
        return the relative database driver class
        If DB_HOST enviroment is not configure, return fake db driver that will do nothing
        :param table_class: the table class define in app folder
        :return:
        """

        DB_HOST = os.getenv("DB_HOST", None)
        if DB_HOST is None:
            return FakeDBDriver()

        if table_class == "Host":  # Physical server
            return HostDriver()
        elif table_class == "VirtHost":  # Virtual machine
            return VirtualHostDriver()
        else:
            raise NotImplementedError()
