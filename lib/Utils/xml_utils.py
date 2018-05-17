#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 File Name: xml_utils.py
 Author: longhui
 Created Time: 2018-05-17 14:15:00
"""
from lxml import etree
from lib.Log.log import log


def validate(schemaFile, xmlFile):
    try:
        with open(schemaFile) as f:
            schemaDoc = etree.parse(f)
            schema = etree.XMLSchema(schemaDoc)

        with open(xmlFile) as f:
            xmlDoc = etree.parse(f)
        schema.assert_(xmlDoc)
    except Exception, e:
        log.exception(str(e))
        return False

    return True
