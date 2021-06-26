#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File  Name: fake_db_driver.py
 Author: longhui
 Created Time: 2021-6-26 18:24:47
"""


from lib.Db.db_driver import DatabaseDriver


class FakeDBDriver(DatabaseDriver):
    def __init__(self, user="admin", passwd="admin"):
        pass

    def __nonzero__(self):
        """
        rewrite this so that the instance support value test
        :return:
        """
        return True

    def close(self):
        return True

    def create(self, **kwargs):
        return True

    def delete(self, id=None):
        return True

    def update(self, id=None, data=None):
        return True

    def query(self, id=None):
        return True
