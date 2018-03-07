#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 File Name: vm_utils.py
 Author: longhui
 Created Time: 2018-03-06 10:43:55
'''
from ipaddress import ip_address, ip_network, AddressValueError, NetmaskValueError
from lib.Log.log import log


class IpCheck(object):

    @classmethod
    def _ipv4_address_check(cls, ipv4_address, prop_string):
        """
        check the ipv4 address
        :return:
        """
        if ipv4_address.is_multicast:
            log.error("%s cannot be a multicast address, see RFC 3171", prop_string)
            return False

        if ipv4_address.is_loopback:
            log.error("%s cannot be a loopback address, see RFC 3330", prop_string)
            return False

        if ipv4_address.is_link_local:
            log.error("%s cannot be a link-local address, see RFC 3927", prop_string)
            return False

        if ipv4_address.is_unspecified:
            log.error("%s cannot be a unspecified address, see RFC 5735", prop_string)
            return False

        if ipv4_address.is_reserved:
            log.error("%s is other IETF reserved", prop_string)
            return False

        return True

    @classmethod
    def is_valid_ipv4_parameter(cls, dest_ip, netmask, gateway=None):
        '''
        check the validation of the DCN related parameters.
        For the ipaddress APIs, please refer to https://docs.python.org/3/library/ipaddress.html
        original: isValidDcnIpParameters
        '''

        # check the validation of the IP address
        try:
            ip_addr = ip_address(unicode(dest_ip))
        except (AddressValueError, NetmaskValueError, ValueError) as error:
            log.exception(str(error))
            return False
        if not cls._ipv4_address_check(ip_addr, "IP address"):
            return False

        # check the validation of the netmask
        try:
            ip_address_netmask = ip_network(unicode(dest_ip + "/" + netmask), strict=False)
        except (AddressValueError, NetmaskValueError, ValueError) as error:
            log.exception("Invalid IPv4 netmask %s: %s", netmask, str(error))
            return False

        if gateway is None:
            return True

        # check the validation of the gateway
        try:
            ip_gateway = ip_address(unicode(gateway))
        except (AddressValueError, NetmaskValueError, ValueError) as error:
            log.exception(str(error))
            return False
        if not cls._ipv4_address_check(ip_gateway, "gateway address"):
            return False

        # the gateway must be in the same
        if ip_gateway not in ip_address_netmask.hosts():
            log.error("Invalidate gateway address %s, not belong to the subnetwork %s",
                      gateway, ip_address_netmask)
            return False

        return True


def is_IP_pingable(ip_address):
    """
    @retrun: True or False if ip_address pingable
    """
    import os
    ping_cmd = "ping -c1 -W1 %s  >/dev/null 2>&1 " % (ip_address)
    #p = subprocess.Popen(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    #pout, perr = p.communicate()
    if os.system(ping_cmd) == 0:
        log.debug("%s is pingable", ip_address)
        return True
    else:
        log.debug("%s is not pingable", ip_address)
        return False


if __name__ == "__main__":
    ip_addr_network = "92.0.2.0"
    gateway = "92.0.2.1"
    dest_ip = "92.0.2.0"
    netmask = "255.255.255.0"
    print IpCheck.is_valid_ipv4_dcn_parameter(ip_addr_network, netmask, gateway)
    print IpCheck.is_valid_ipv4_dcn_parameter(dest_ip, netmask, gateway=None)
    #import pyping
    #pyping.ping(hostname, timeout, count, packet_size)
    print is_IP_pingable(gateway)
    print is_IP_pingable("localhost")