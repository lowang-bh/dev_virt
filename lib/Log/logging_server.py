#!/usr/bin/env python

# from logging.handlers import RotatingFileHandler

import os
import cPickle
import logging.config
import socket
import struct
import traceback
import threading

'''
 Using log.debug("something") if you just want save this
 log to /var/csim_log/log.log and NOT show to user's screen

 You can use the following log commands:
 log.debug("something")
 log.info("something")
 log.warning("something")
 log.error("something")
 log.critical("something")

 Level   Numeric value
 CRITICAL    50
 ERROR       40
 WARNING     30
 INFO        20
 DEBUG       10
 NOTSET      0

 for more infomation, please reference https://docs.python.org/2/library/logging.html
'''


def start_logging_server(log_name=None, port=12345):
    '''
    '''
    logging.config.fileConfig(os.path.join(os.path.dirname(__file__), "logging_server.conf"))
    log = logging.getLogger(log_name)
    host = ''

    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    so.bind((host, port))

    while 1:
        try:
            msg = so.recv(8192)
            offset = struct.calcsize(">L")
            slen = struct.unpack(">L", msg[0:offset])[0]
            record = logging.makeLogRecord(cPickle.loads(msg[offset:]))
            # open the print when "not all arguments converted during string formatting" can locate the error
            # sys.stdout.write(str(record.name) + str(record.msg) + str(record.args) + "\n")
            # sys.stdout.flush()
            log.handle(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # This can not print the message when error "not all arguments converted during string formatting" occur
            # sys.stdout.write(str(record.msg) + str(record.args) + "\n")
            # sys.stdout.flush()
            traceback.print_exc()


if __name__ == "__main__":
    log_thread = threading.Thread(name="root_log", target=start_logging_server, args=(None, 12345))
    log_thread.setDaemon(False)
    nohup_log_thread = threading.Thread(name="nohup", target=start_logging_server, args=("nohup", 12346))
    nohup_log_thread.setDaemon(False)

    log_thread.start()
    nohup_log_thread.start()

