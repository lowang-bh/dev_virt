#!/usr/bin/env bash
#########################################################################
# File Name: set_ip.sh
# Author: longhui
# Created Time: 2018-03-08 15:40:59
# Description: The script is to set the ip on eth0 through its mac address.
#              If the mac start with "00:66", then use this method to setup
#              the IP when system start up
#########################################################################
set -eu

if [[ $# == 1 ]];then
    myeth=$1
else
    myeth=eth0
fi

mymac=`ifconfig $myeth | awk '/HWaddr\ / {print $5}'`

if [[ x$mymac == x"" ]];then
    echo "No HWaddr find, try another pattern"
    mymac=`ifconfig $myeth | awk '/ether\ / {print $2}'`

    if [[ x$mymac == x"" ]];then
        echo "Can not match Hwaddr or ether, exiting..."
        exit 1
    fi
fi

GetMacNum()
{
	str=`echo $1 | cut -d':' -f$2`
	num=`printf "%d" 0x$str`
	echo $num
}

if [[ $mymac == 00:66* ]];then
    echo "start to config IP based on MAC."
    num1st=`GetMacNum $mymac 3`
    num2ed=`GetMacNum $mymac 4`
    num3rd=`GetMacNum $mymac 5`
    num4th=`GetMacNum $mymac 6`

    MyIP=$num1st.$num2ed.$num3rd.$num4th

    MyGW=`echo $MyIP | awk -F. '{print $1"."$2"."$3".1"}'`
    MyBC=`echo $MyIP | awk -F. '{print $1"."$2"."$3".255"}'`

    echo "IPADDR=$MyIP" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
    echo "GATEWAY=$MyGW" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
    echo "BROADCAST=$MyBC" >> /etc/sysconfig/network-scripts/ifcfg-$myeth
else
    echo "No MAC match the default pattern, exiting"
fi
