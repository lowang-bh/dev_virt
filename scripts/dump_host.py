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
from lib.Utils.server_utils import ServerDomain

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
    parser.add_option("--list-pif", dest="list_pif", action="store_true", help="List all the interface information")
    parser.add_option("--list-bond", dest="list_bond", action="store_true", help="List all the bond information")

    (options, args) = parser.parse_args()
    log.debug("options:%s, args:%s", str(options), str(args))

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)
    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""

    serverDomain = ServerDomain(host_name, user, passwd)
    if not serverDomain:
        log.fail("Can not connect to virtual driver or DB driver, initial serverDomain failed.")
        exit(1)

    if options.list_sr:
        log.info("Host Storage informations:")
        storage = serverDomain.get_host_all_storage_info()
        for k, v in storage.iteritems():
            log.info("%-15s: \tTotal: %8sGB, Free:%8sGB", k, v[0], v[1])
    elif options.list_pif:
        serverDomain.print_all_interface()
    elif options.list_bond:
        serverDomain.print_bond_inforation()
    else:
        serverDomain.print_server_hardware_info()

    exit(0)
