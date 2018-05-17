#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: setup_system.py
 Author: longhui
 Created Time: 2018-05-17 13:11:04
 This script is used to create multiple VMS in multiple xenservers by parse the given xml
"""

from lib.Log.log import log
import lib.Utils.xml_utils as xml_utils

if not xml_utils.validate("../etc/schema.xsd", "../../etc/example.xml"):
    log.error("XML file (" + "example.xml" + ") did not validate")
