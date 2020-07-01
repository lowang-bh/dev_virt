#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: constans.py
 Author: longhui
 Created Time: 2019-04-24 11:07:34
 Description: lain3 node for k8s cluster default config
"""
template_dict = {

    "master": {"cpu": 8, "memory": 16, "template": "k8s-template"},
    "ingress": {"cpu": 8, "memory": 16, "template": "k8s-template"},
    "node": {"cpu": 16, "memory": 32, "template": "k8s-template", "disk_size": 200, "add_disk_num": 1},
    "etcd": {"cpu": 4, "memory": 8, "template": "k8s-template", "disk_size": 100, "add_disk_num": 1},
    "jenkins": {"cpu": 8, "memory": 32, "template": "template", "disk_size": 100, "add_disk_num": 2},
    }

DISK_POOL = "kvm-disk-pool"
NETFS_POOL_TYPE="netfs"
DEFAULT_NETWORK = "libvirtmgr-net"
MEMORY_OVERCOMMIT_FRACTION = 1.2
Libvirtd_User = "admin"
Libvirtd_Pass = "admin"
