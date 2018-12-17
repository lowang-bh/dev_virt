#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: host_driver.py
 Author: longhui
 Created Time: 2018-03-27 10:14:53
"""

import json

import requests

from app.cmdb.settings import DB_HOST, LOGOUT_URL, LOGIN_URL
from lib.Db.db_driver import DatabaseDriver
from lib.Log.log import log


class HostDbDriver(DatabaseDriver):
    def __init__(self, user="admin", passwd="admin"):
        super(HostDbDriver, self).__init__(user, passwd)
        self.db_host = DB_HOST
        self.login_url = LOGIN_URL
        self.logout_url = LOGOUT_URL
        self.url = None

        login_data = {'username': self.user, 'password': self.passwd}

        try:
            self.session = requests.Session()
            login_res = self.session.post(self.login_url, data=login_data)
            res_content = json.loads(login_res.content)

            if res_content['status'] == 1:  # the success check depend on the login html
                log.debug("Login url [%s] check with username [%s] success.", self.db_host, self.user)
            else:
                log.error("Login url [%s] check with username [%s] failed.", self.db_host, self.user)
                self.session = None
        except requests.exceptions.ConnectionError as connerror:
            log.exception("Connection exception: %s", connerror)
            self.session = None
        except Exception as error:
            log.exception("Exception when init session: %s", error)
            self.session = None

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
        :return: a list of records and each record is a dict
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
    def respond_errors(self):
        """
        :return: the errors in response
        """
        return self.respond_data.get('errors', "Can not get errors.")

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
