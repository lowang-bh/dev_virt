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
from app.settings import DB_HOST, LOGIN_URL, LOGOUT_URL


@six.add_metaclass(abc.ABCMeta)
class DatabaseDriver(object):

    def __init__(self, user="admin", passwd="access"):
        self.user = user
        self.passwd = passwd
        self.db_host = DB_HOST
        self.login_url = LOGIN_URL
        self.logout_url = LOGOUT_URL
        self.url = None
        self.session = None
        self.resp = None

        login_data = {'username': self.user, 'password': self.passwd}

        self.session = requests.Session()

        login_res = self.session.post(self.login_url, data=login_data)
        res_content = json.loads(login_res.content)

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

    def __enter__(self):
        log.debug("return database driver.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug("close session connected to db")
        self.close()

    def close(self):
        """
        logout and close the session
        :return:
        """
        self.session.get(self.logout_url)
        self.session.cookies.clear()
        self.session.close()
        self.session = None

    @classmethod
    def db_name(cls, url):
        """
        :param url:
        :return:
        """
        return "/".join(url.strip('/').split('/')[3:])

    @property
    def respond_data(self):
        """
        return the HTTP response data
        :return:
        """
        try:
            if isinstance(self.resp, requests.models.Response):
                return json.loads(self.resp.content).get('data', {})
            elif isinstance(self.resp, str):
                return json.loads(self.resp).get('data', {})
            elif isinstance(self.resp, dict):
                return self.resp.get('data', {})
        except ValueError, error:
            log.exception(error)

        return {}

    @property
    def respond_data_count(self):
        """
        :return: return the record counts in response
        """
        count = self.respond_data.get("count", 0)
        return int(count)

    @property
    def respond_data_list(self):
        """
        return the respond data list
        :return:
        """
        return self.respond_data.get("list", [])

    @property
    def is_respond_error(self):
        """
        return True is error occur in the content else False
        :return:
        """
        if "errors" in self.respond_data:
            return True

        return False

    @property
    def respond_msg(self):
        """
        return the msg in http response content
        :return:
        """
        if isinstance(self.resp, requests.models.Response):
            return json.loads(self.resp.content).get("msg", "")
        elif isinstance(self.resp, str):
            return json.loads(self.resp).get("msg", "")
        elif isinstance(self.resp, dict):
            return self.resp.get("msg", "")

        return ""

    @property
    def respond_code(self):
        """
        return the HTTP response code
        :return:
        """
        if isinstance(self.resp, requests.models.Response):
            return json.loads(self.resp.content).get("code", None)
        elif isinstance(self.resp, str):
            return json.loads(self.resp).get("code", None)
        elif isinstance(self.resp, dict):
            return self.resp.get("code", None)

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
