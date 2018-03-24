#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: dump_host.py
 Author: longhui
 Created Time: 2018-03-13 18:32:39
 Descriptions: Dump the information about the host
'''
from optparse import OptionParser
from lib.Log.log import log
from lib.Utils.server_utils import print_server_hardware_info, get_host_all_storage_info

if __name__ == "__main__":
    usage = """usage: %prog [options] vm_name\n
        dump_host.py    [--host=ip --user=user --pwd=passwd]
        dump_host.py --list-sr [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    parser.add_option("--list-sr", dest="list_sr", action="store_true", help="List all the storage information")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    option_dic = {"host":options.host, "user":options.user, "passwd":options.passwd}
    if options.list_sr:
        log.info("Host Storage informations:")
        storage = get_host_all_storage_info(**option_dic)
        for k, v in storage.iteritems():
            log.info("%-15s: \tTotal: %8sGB, Free:%8sGB", k, v[0], v[1])
    else:
        print_server_hardware_info(**option_dic)

    exit(0)
