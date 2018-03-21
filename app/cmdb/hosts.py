#!/usr/bin/env python
# -*- coding:UTF-8 -*-

import json
import requests
from lib.Log.log import log

def create_object_to_data(session, url, data):
    """
    write data to db
    :param url:
    :param data:
    :return: True or False
    """
    res = session.post(url, data=data)
    db_name = "/".join(url.strip('/').split('/')[3:])
    if res.status_code == requests.codes.ok:
        log.info("Update data to database: [%s] successfully.", db_name)
        return True
    else:
        log.error("Update data to database: [%s] failed.", db_name)
        res_dict_data = json.loads(res.content)['data']
        #{"msg":"执行异常！","code":400,"data":{"errors":{"sn":["具有 sn 的 hosts 已存在。"]}}}
        #errors in data
        return False
