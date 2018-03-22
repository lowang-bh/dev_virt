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

    def __init__(self, user="admin", passwd="access"):
        self.user = user
        self.passwd = passwd
        self.db_host = DB_HOST
        self.login_url = LOGIN_URL
        self.url = None
        self.session = None
        self.resp = None

        login_data = {'username': self.user, 'password': self.passwd}

        self.session = requests.Session()

        login_res = self.session.post(self.login_url, data=login_data)
        res_content = json.loads(login_res.content)
        print type(res_content), res_content

        if res_content['status'] == 1:  # the success check depend on the login html
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

    @classmethod
    def db_name(cls, url):
        """
        :param url:
        :return:
        """
        return "/".join(url.strip('/').split('/')[3:])

    @classmethod
    def respond_data(cls, content):
        """
        return the HTTP response data
        :param content:
        :return:
        """
        if isinstance(content, dict):
            return content['data']
        elif isinstance(content, str):
            return json.loads(content)['data']

        return {}

    @classmethod
    def is_respond_error(cls, content):
        """
        return True is error occur in the content else False
        :param content:
        :return:
        """
        if "errors" in cls.respond_data(content):
            return True

        return False

    @classmethod
    def respond_msg(cls, content):
        """
        return the msg in http response content
        :param content:
        :return:
        """
        if isinstance(content, dict):
            return content.get("msg", "")
        elif isinstance(content, str):
            return json.loads(content).get("msg", "")

        return ""

    @classmethod
    def respond_code(cls, content):
        """
        return the HTTP response code
        :param content:
        :return:
        """
        if isinstance(content, dict):
            return content.get('code', None)
        elif isinstance(content, str):
            return json.loads(content).get("code", None)

        return None

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
