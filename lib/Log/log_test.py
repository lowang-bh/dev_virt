#!/usr/bin/env python
# ! -*- coding: utf-8 -*-
#########################################################################
# File Name: lib/Log/log_test.py
# Author: longhui
# Created Time: 2018-02-11 18:44:19
#########################################################################

import logging
from lib.Log.log import log, nohup_log
nohup_orig_log = logging.getLogger("nohup")
thread_log = logging.getLogger("thread")
rotate_log = logging.getLogger('virt')

log.info("thread_log")
thread_log.debug("thread_log test log for debug.")
thread_log.info("thread_log test log for info")
thread_log.warning("thread_log test log for warning")
thread_log.error("thread_log test log for error")
thread_log.exception("thread_log test log for exception")

log.info("nohup_orig_log")
nohup_orig_log.debug("test log for debug.")
nohup_orig_log.info("test log for info")
nohup_orig_log.warning("test log for warning")
nohup_orig_log.error("test log for error")
nohup_orig_log.exception("test log for exception")
log.info("nohup log")
nohup_log.debug("nohup test log for debug.")
nohup_log.info("nohup test log for info")
nohup_log.warning("nohup test log for warning")
nohup_log.error("nohup test log for error")
nohup_log.exception("nohup test log for exception")

log.info("rotate_log")
rotate_log.debug("test log for debug.")
rotate_log.info("test log for info")
rotate_log.warning("test log for warning")
rotate_log.error("test log for error")
rotate_log.exception("test log for exception")

log.info("virt console")
log.debug("test log for debug.")
log.info("test log for info")
log.warning("test log for warning")
log.error("test log for error")
log.exception("test log for exception")
log.success("test log for success")
log.fail("test log for fail")
