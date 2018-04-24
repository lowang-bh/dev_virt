#!/usr/bin/env python


import os
# DB_HOST = "http://127.0.0.1:8000"
db_host = os.getenv("DB_HOST", "127.0.0.1:8000")
DB_HOST = "http://%s" % (db_host)

LOGIN_URL = DB_HOST + '/user/logincheck'
LOGOUT_URL = DB_HOST + '/user/logout'

HOSTs_URL = DB_HOST + '/cmdb/hosts/'
HOSTGROUP_URL = DB_HOST + '/cmdb/hostgroup/'
