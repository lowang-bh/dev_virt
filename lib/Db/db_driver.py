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
from app.settings import DB_HOST, LOGIN_URL


@six.add_metaclass(abc.ABCMeta)
class DatabaseDriver(object):

    def __init__(self, user="root", passwd="access"):
        self.user = user
        self.passwd = passwd
        self.db_host = DB_HOST
        self.login_url = LOGIN_URL
        self.session = None

        login_data = {'username': self.user, 'password': self.passwd}

        self.session = requests.Session()

        login_res = self.session.post(self.login_url, data=login_data)
        res_content = json.loads(login_res.content)

        if res_content.status == 1:  # the success check depend on the login html
            log.debug("login db_host [%s] with username [%s] success.", self.db_host, self.user)
        else:
            log.error("Login db_host [%s] with username [%s] failed.", self.db_host, self.user)
            self.session = None

    def __nonzero__(self):
        """
        rewrite this so that the instance support value test
        :return:
        """
        if self.session is None:
            return False
        else:
            return True

    @abc.abstractmethod
    def create(self, data=None):
        """
        create a record to database
        :param data: dict data use to request
        :return:True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, pk=None):
        """
        Delete a record from database
        :param pk:
        :return:
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, pk=None, data=None):
        """
        update the data to a record with its primary key is pk
        :param pk:
        :param data:
        :return: True or False
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def query(self, pk=None):
        """
        query from database
        :param pk:
        :return: the record with Dict
        """
        raise NotImplementedError()
