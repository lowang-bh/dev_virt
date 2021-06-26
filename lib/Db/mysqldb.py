#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: lib/Db/mysqldb.py
 Author: longhui
 Created Time: 2019-04-24 17:28:11
"""

import MySQLdb
from lib.Utils.signal_utils import timeout_decrator, TimeoutError


class MysqlDB(object):
    def __init__(self, host="127.0.0.1", user="root", passwd="rootpassword", port=3306, db="cmdb"):
        self._host=host
        self._user=user
        self._passwd = passwd
        self._port = port
        self._db=db
        self.conn = None #MySQLdb.connect(host=host, user=user, password=passwd, port=port, database=db)
        self.cursor = None
    
    @timeout_decrator(6)
    def connect(self):
        if self.conn is None:
            self.conn =  MySQLdb.connect(host=self._host, 
                                         user=self._user, 
                                         password=self._passwd, 
                                         port=self._port, 
                                         database=self._db)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        
    def __nonzero__(self):
        return self.conn is not None

    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type is not None:
            return False # reraise exception
        else:
            return True
    
    def get_kvm_host_list(self):
        """
        :return: kvm host ip list
        """
        self.cursor.execute("select first_ip from cmdb_hosts where device_type='KVM Host' and machine_type='物理机';")
        return [ip[0] for ip in self.cursor.fetchall()]
    
    def get_firt_ip_list(self):
        """
        :return: all the ip on veth 0 used by vm in cmdb
        """
        self.cursor.execute("select first_ip from cmdb_hosts where first_ip != 'NULL';")
        return [ip[0] for ip in self.cursor.fetchall()]
        
    def get_second_ip_list(self):
        """
        :return: return a list of all second ip
        """
        self.cursor.execute("select second_ip from cmdb_hosts where second_ip != 'NULL';")     
        return [ip[0] for ip in self.cursor.fetchall()]
    
    def get_vip_list(self):
        """
        :return: a list of vip 
        """
        self.cursor.execute("select virtual_ip from cmdb_virtual_ip;")
        return [ip[0] for ip in self.cursor.fetchall()]
    
    def get_vm_name_list(self, key=None):
        if key:
            query = "select hostname from cmdb_hosts where hostname like '%%%s%%' and  machine_type='虚拟机';" %key
        else:
            query = "select hostname from cmdb_hosts where machine_type='虚拟机';"
            
        self.cursor.execute(query)
        return [name[0] for name in self.cursor.fetchall()]

        
    def get_kvm_vmname_list(self, key=None):
        """
        :return: return vm name list with key in name
        """
        if key:
            query = "select hostname from cmdb_hosts where hostname like 'kvm%%%s%%' and  machine_type='虚拟机';" %key
        else:
            query = "select hostname from cmdb_hosts where hostname like 'kvm%' and machine_type='虚拟机';"
            
        self.cursor.execute(query)
        return [name[0] for name in self.cursor.fetchall()]




if __name__ == "__main__":
    try:
        with MysqlDB() as dbconn:
            print(dbconn.get_kvm_host_list())
            print(dbconn.get_second_ip_list())
            print(dbconn.get_vip_list())
            names = dbconn.get_kvm_vmname_list("k8s-master")
            for name in names:
                print(name)
            print(len(names))
    except TimeoutError:
        print("timeout")
