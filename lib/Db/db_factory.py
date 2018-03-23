#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: db_factory.py
 Author: longhui
 Created Time: 2018-03-22 20:33:04
 Descriptions: The factory class for Database crud
'''

from app.cmdb.hosts import HostDriver, VirtualHostDriver

class DbFactory(object):

    @classmethod
    def get_db_driver(cls, table_class):
        """
        return the relative database driver class
        :param table_class: the table class define in app folder
        :return:
        """
        if table_class == "Host": # Physical server
            return HostDriver()
        elif table_class == "VirtHost": # Virtual machine
            return VirtualHostDriver()
        else:
            raise NotImplementedError()
