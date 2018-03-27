#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################################
# File Name: db_driver.py
# Attentions: This file is used as driver to write db data via send requests to django API
# Author: longhui
# Created Time: 2018-02-08 11:18:37
#########################################################################

import abc
import six
import requests
import json

from lib.Log.log import log


@six.add_metaclass(abc.ABCMeta)
class DatabaseDriver(object):

    def __init__(self, user="admin", passwd="access"):
        self.user = user
        self.passwd = passwd
        self.session = None
        self.resp = None

    def __nonzero__(self):
        """
        rewrite this so that the instance support value test
        :return:
        """
        if self.session is None:
            return False
        else:
            return True

    def __enter__(self):
        log.debug("return database driver.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug("close session connected to db")
        self.close()

    @abc.abstractmethod
    def close(self):
        """
        logout and close the session
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def create(self, **kwargs):
        """
        create a record to database
        :param data: dict data use to request
        :return:True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, id=None):
        """
        Delete a record from database
        :param id:
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, id=None, data=None):
        """
        update the data to a record with its primary key is pk
        :param id:
        :param data:
        :return: True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def query(self, id=None):
        """
        query from database
        :param id:
        :return: the record with Dict
        """
        raise NotImplementedError()
