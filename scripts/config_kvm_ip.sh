#!/usr/bin/env bash
#########################################################################
# File Name: set_ip.sh
# Author: longhui
# Created Time: 2018-03-08 15:40:59
# Description: The script is to set the ip on eth0 through its mac address.
#              If the mac start with "52:54", then use this method to setup
#              the IP when system start up
#########################################################################
set -u

if [[ $# == 1 ]];then
    myeth=$1
else
    myeth=eth0
fi

mymac=`ifconfig $myeth | awk '/HWaddr\ / {print $5}'`

if [[ x$mymac == x"" ]];then
    echo "No HWaddr find on $myeth, try another pattern"
    mymac=`ifconfig $myeth | awk '/ether\ / {print $2}'`

    if [[ x$mymac == x"" ]];then
        echo "Can not match Hwaddr or ether on $myeth, exiting..."
        exit 1
    fi
fi

GetMacNum()
{
	str=`echo $1 | cut -d':' -f$2`
	num=`printf "%d" 0x$str`
	echo $num
}

if [[ $mymac == 52:54:* ]];then
    echo "start to config IP based on MAC."
    num1st=`GetMacNum $mymac 3`
    num2ed=`GetMacNum $mymac 4`
    num3rd=`GetMacNum $mymac 5`
    num4th=`GetMacNum $mymac 6`

    if [[ $num1st -eq 10 || $num1st -eq 172 ]];then
    	MyIP=$num1st.$num2ed.$num3rd.$num4th
    else
	    MyIP=192.$num2ed.$num3rd.$num4th
    fi

    MyGW=`echo $MyIP | awk -F. '{print $1"."$2"."$3".1"}'`
    MyBC=`echo $MyIP | awk -F. '{print $1"."$2"."$3".255"}'`
    if [[ ! -f /etc/sysconfig/network-scripts/ifcfg-$myeth ]];then
        touch /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "TYPE=Ethernet" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "BOOTPROTO=static" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "NAME=$myeth" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "ONBOOT=yes" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "PREFIX=24" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
    fi
    grep_res=$(grep "IPADDR=" /etc/sysconfig/network-scripts/ifcfg-$myeth 2> /dev/null)
    if [[ $grep_res != IPADDR=* && -f /etc/sysconfig/network-scripts/ifcfg-$myeth ]];then
        echo "write ip to /etc/sysconfig/network-scripts/ifcfg-$myeth"
        echo "IPADDR=$MyIP" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "GATEWAY=$MyGW" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "BROADCAST=$MyBC" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
        echo "DNS1=8.8.8.8" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
    elif [[ $grep_res == IPADDR=* ]];then
        echo "origin IP on $myeth:$grep_res, set to new: $MyIP"
        sed -i "s/^IPADDR=.*$/IPADDR=$MyIP/" /etc/sysconfig/network-scripts/ifcfg-$myeth
    else
        echo "Already configed $myeth"
    fi
    #write the MAC to configfile, in case of the ip will be randomly on interface when restart network
    grep "HWADDR" /etc/sysconfig/network-scripts/ifcfg-$myeth 2> /dev/null
    if [[ $? -eq 0 ]];then
        sed -i "s/^HWADDR=.*$/HWADDR=$mymac/" /etc/sysconfig/network-scripts/ifcfg-$myeth
    else
        sed -i "/IPADDR/a\HWADDR=$mymac" /etc/sysconfig/network-scripts/ifcfg-$myeth
    fi

    #config the IP when system up
    ifconfig $myeth $MyIP netmask 255.255.255.0
    #add default GW only when gw match the IP 10.* for a whole net, other IP as 192.168* will discard
    if [[ $MyGW == 10.* ]];then
        route add default gw $MyGW
    fi
else
    echo "No MAC match the default pattern, exiting"
fi

