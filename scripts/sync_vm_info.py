#!/usr/bin/env python
# -*- coding: utf-8 -*-


from optparse import OptionParser
from lib.Log.log import log
from lib.Val.virt_factory import VirtFactory
from lib.Utils.vm_utils import VirtHostDomain
from lib.Utils.server_utils import ServerDomain

if __name__ == "__main__":
    usage = """usage: %prog [options] arg1 arg2\n
        
        Sync the information about the host and all VMs to database.
        
        sync_vm_info.py             [--host=ip --user=user --pwd=passwd]
        sync_vm_info.py --vm=vmname [--host=ip --user=user --pwd=passwd]
        """

    parser = OptionParser(usage=usage)
    parser.add_option("--host", dest="host", help="IP for host server")
    parser.add_option("-u", "--user", dest="user", help="User name for host server")
    parser.add_option("-p", "--pwd", dest="passwd", help="Passward for host server")
    parser.add_option("--vm", dest="vm_name", help="Sync the VM's infor to database")

    (options, args) = parser.parse_args()
    log.debug("options: %s, args: %s", options, args)

    if options.host is not None and (options.user is None or options.passwd is None):
        log.fail("Please specify a user-name and passward for the given host:%s", options.host)
        exit(1)

    host_name = options.host
    user = options.user if options.user else "root"
    passwd = str(options.passwd).replace('\\', '') if options.passwd else ""


    if options.vm_name:
        virt_host = VirtHostDomain(host_name, user, passwd)
        if not virt_host:
            log.fail("Can not connect to virtual driver, initial VirtHostDomain failed.")
            exit(1)
        if not virt_host.virt_driver.is_instance_exists(options.vm_name):
            log.fail("VM [%s] doesn't exist. Exiting...", options.vm_name)
            exit(1)
        if virt_host.update_database_info(inst_name=options.vm_name):
            log.success("Sync VM [%s] information successfully.", options.vm_name)
            exit(0)
        else:
            log.fail("Sync VM [%s] information failed.", options.vm_name)
    else:
        server = ServerDomain(host_name, user, passwd)
        if not server:
            log.fail("Can not connect to virtual driver, initial HostDomain failed.")
            exit(1)
        server.create_database_info()
        server.update_database_info()
        virt_host = VirtHostDomain(host_name, user, passwd)
        for vm_name in virt_host.virt_driver.get_vm_list():
            # TODO sync IP
            virt_host.create_database_info(inst_name=vm_name)
            virt_host.update_database_info(inst_name=vm_name)


