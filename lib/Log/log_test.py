#!/usr/bin/env python
# ! -*- coding: utf-8 -*-
#########################################################################
# File Name: lib/Log/log_test.py
# Author: longhui
# Created Time: 2018-02-11 18:44:19
#########################################################################
print "test log"
import logging
from log import log
nohup_log = logging.getLogger("nohup")
thread_log = logging.getLogger("thread")
rotate_log = logging.getLogger('virt')

print "thread_log"
thread_log.debug("test log for debug.")
thread_log.info("test log for info")
thread_log.warning("test log for warning")
thread_log.error("test log for error")
thread_log.exception("test log for exception")

print "nohup_log"
nohup_log.debug("test log for debug.")
nohup_log.info("test log for info")
nohup_log.warning("test log for warning")
nohup_log.error("test log for error")
nohup_log.exception("test log for exception")

print "rotate_log"
rotate_log.debug("test log for debug.")
rotate_log.info("test log for info")
rotate_log.warning("test log for warning")
rotate_log.error("test log for error")
rotate_log.exception("test log for exception")

log.debug("test log for debug.")
log.info("test log for info")
log.warning("test log for warning")
log.error("test log for error")
log.exception("test log for exception")
