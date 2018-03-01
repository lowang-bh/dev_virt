#!/usr/bin/env python

"""
This library contains modules for logging system.

if use it, plase import it as following

from lib.Log.log import log

then add log where you want to add

log.debug(message)
log.info(message)
log.warn(message)
log.warning(message)
log.error(message)
log.critical(message)
log.fatal(message)
log.exception(message)  # this is commenly use to log the exception call stack

"""

import logging
import os, sys, traceback
import logging.config
from logging import handlers, INFO, ERROR, WARNING, DEBUG

log_path = os.path.join(os.getenv("HOME"), 'virt_log')


class virt_log(logging.Logger):

    def __init__(self, name):
        logging.Logger.__init__(self, name)

    def get_frame_info(self):
        '''
        return the filename, lineno, funcname where the log is called
        '''
        try:
            f = sys._getframe(3)
            co = f.f_code
            rv = (co.co_filename, f.f_lineno, co.co_name)
        except (ValueError, AttributeError):
            rv = ("(unknown file)", 0, "(unknown function)")
        finally:
            return rv

    def print_callstack(self):
        '''
        When error ocur, use this function to print the callstack so that
        it easy to find the error path
        '''
        try:
            f = sys._getframe(3)
            while hasattr(f, "f_code"):
                co = f.f_code
                fn, lno, func = (co.co_filename, f.f_lineno, co.co_name)
                self.debug("%-35s, %4s, %s", fn, lno, func)
                f = f.f_back
        except Exception:
            return

    def __log(self, level, msg, args, exc_info=None, extra=None):
        '''
        Use self defined log to handle log, similar to the logging model
        '''
        fn, lno, func = self.get_frame_info()  # self.find_caller() also can be used, but need to handle exception
        record = self.makeRecord(self.name, level, fn, lno, msg, args, exc_info, func, extra)
        self.handle(record)
        if level == ERROR:
            self.print_callstack()

    def success(self, msg, *args, **kwargs):
        '''
        Used for  log when print SUCCESS message
        Key text [SUCCESS] will be show as: highlight;green;black backgroud
        '''
        msg = "\033[1;32;40m[SUCCESS] %s\033[0;0;0m" % (msg)
        if self.isEnabledFor(INFO):
            self.__log(INFO, msg, args, **kwargs)

    def fail(self, msg, *args, **kwargs):
        '''
        Used for  log when print FAILURE message
        Key text [FAILURE] will be show as: highlight;red;black backgroud
        '''
        msg = "\033[1;31;40m[FAILURE] %s\033[0;0;0m" % (msg)
        if self.isEnabledFor(ERROR):
            self.__log(ERROR, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        '''
        Used for  log when print SUCCESS message
        Key text [SUCCESS] will be show as: highlight;green;black backgroud
        '''
        msg = "\033[1;32;40m[  INFO ] %s\033[0;0;0m" % (msg)
        if self.isEnabledFor(INFO):
            self.__log(INFO, msg, args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        '''
        Used for  log when print WARNING message
        Key text [WARNING] will be show as: highlight;yellow;black backgroud
        '''
        msg = "\033[1;33;40m[WARNING] %s\033[0;0;0m" % (msg)
        if self.isEnabledFor(WARNING):
            self.__log(WARNING, msg, args, **kwargs)

    warning = warn

    def error(self, msg, *args, **kwargs):
        '''
        Key text [ERROR] will be show as: highlight;red;black backgroud
        '''
        msg = "\033[1;31;40m[ ERROR ] %s\033[0;0;0m" % (msg)
        if self.isEnabledFor(ERROR):
            self.__log(ERROR, msg, args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        '''
        Used for  log when print EXCEPTION message
        '''
        format_str = traceback.format_exc()
        if isinstance(msg, str):
            msg = "\033[1;31;40m[ ERROR ] %s\033[0;0;0m" % (msg)
            self.__log(ERROR, msg, args, **kwargs)

        format_str = "\n" + format_str
        self.__log(DEBUG, format_str, (), {})


if not os.path.exists(log_path):
    os.mkdir(log_path)

# The logging.conf can not be replaced by logging_server.conf,
# if so, log can not written to log.log if its mode is 644

conf_file = os.path.join(os.path.dirname(__file__), "logging.conf")
#print conf_file
logging.config.fileConfig(conf_file)
log = virt_log("virt")
temp_log = logging.getLogger("virt")
log.setLevel(temp_log.level)
for handler in temp_log.handlers:
    log.addHandler(handler)
#===============================================================================
# # print log to console
# log.propagate = 0
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.INFO)
# handler.setFormatter(logging.Formatter("%(message)s"))
# log.addHandler(handler)
#
# # pass log to socket
# sock_handler = handlers.DatagramHandler('localhost', 12345)
# log.addHandler(sock_handler)
#===============================================================================

# backgroud process log
# nohup_log = logging.getLogger("nohup")
#===============================================================================
# nohup_temp_log = logging.getLogger("nohup")
# nohup_log = virt_log("nohup")
# nohup_log.setLevel(nohup_temp_log.level)
# for handler in nohup_temp_log.handlers:
#     nohup_log.addHandler(handler)
#===============================================================================

# mod_syspvt record log
#===============================================================================
# syspvt_temp_log = logging.getLogger("syspvt")
# syspvt_log = virt_log("syspvt")
# syspvt_log.setLevel(syspvt_temp_log.level)
# for handler in syspvt_temp_log.handlers:
#     syspvt_log.addHandler(handler)
#===============================================================================
# thread log install image and attach SC to NC
# thread_log = logging.getLogger("thread")

