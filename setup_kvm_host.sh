#!/usr/bin/env bash

set -euo pipefail

if [ $EUID -ne 0 ];then
    echo "You must be root (or sudo) to run this script"
    exit 1
fi

BASEDIR=`pwd`
touch LOGFILE
touch MESSAGE
message()
{
    echo `date '+%Y-%m-%d %H:%M:%S'` "$1" |tee -a MESSAGE
}

if [[ ! -e /etc/pki/CA/cacert.pem ]];then
    message "Please restart libvirtd after you setup the certifications for libvirt..."
    exit 1
fi

install_basic_pkg()
{
message "Start to install basic pkg: expect, VIM and bash-completion for server..."

yum -y install expect >> LOGFILE
if [[ $? -ne 0 ]];then
    message "Failure: expect install failed"
fi
yum -y install bash-completion >> LOGFILE
if [[ $? -ne 0 ]];then
    message "Failure: bash-completion install failed"
fi

#if [[ -f /etc/profile.d/bash_completion.sh ]];then
#    source /etc/profile.d/bash_completion.sh
#fi

yum -y install mlocate >> LOGFILE
yum -y install vim >> LOGFILE
rpm -qa |grep python-devel || yum -y install python-devel >>LOGFILE
yum -y install gcc >>LOGFILE
}

config_vim()
{
cat >>/etc/vimrc<<EOF
set hlsearch
set fileformat=unix
set showmatch
set number
set tabstop=4 expandtab shiftwidth=4
set softtabstop=4
EOF
}

do_basic_config()
{
echo "export HISTTIMEFORMAT='%F %T '" >> /etc/bashrc
echo 'export EDITOR=vim' >> /etc/bashrc

message "Start to config VIM..."
config_vim

}

if [[ -z $(grep HISTTIMEFORMAT /etc/bashrc) ]];then
    message "Start to do basic config for server..."
    install_basic_pkg
    do_basic_config
else
    message "Basic config already done, ignore..."
fi

message "Start to install lib for KVM..."
egrep -q '(vmx|svm)' /proc/cpuinfo
if [[ $? -ne 0 ]];then
    message "Your host doesn't support KVM virtulization, please make sure the virtual cpu is turn on"
    exit 1
fi

yum -y install cyrus-sasl-plain cyrus-sasl-scram cyrus-sasl-lib cyrus-sasl-devel cyrus-sasl-gssapi cyrus-sasl

message "Start to install qemu-kvm,qemu-img,libvirt,virt-clone,virt-install..."

rpm -aq|grep bridge-utils  || yum -y install bridge-utils  >>LOGFILE
rpm -aq|grep qemu-kvm || yum -y install qemu-kvm >>LOGFILE
rpm -aq|grep qemu-img || yum -y install qemu-img >>LOGFILE
rpm -aq|grep libvirt || yum -y install libvirt >>LOGFILE
rpm -aq|grep libvirt-devel || yum -y install libvirt-devel >>LOGFILE
rpm -qa|grep virt-install || yum -y install virt-install >>LOGFILE
rpm -aq|grep virt-clone || yum -y install virt-clone >>LOGFILE
rpm -aq|grep libguestfs-tools || yum -y install libguestfs-tools >>LOGFILE
rpm -aq|grep libguestfs-winsupport || yum -y install libguestfs-winsupport >>LOGFILE

modprobe kvm_intel
lsmod |grep kvm
if [[ $? -ne 0 ]];then
    message "kvm module insert failed, please check it"
    exit 1
fi

configure_libvirtd()
{

cp /etc/libvirt/libvirtd.conf /etc/libvirt/libvirtd-bak.conf
cp /etc/sysconfig/libvirtd    /etc/sysconfig/libvirtd-bak
cp /etc/libvirt/qemu.conf     /etc/libvirt/qemu-bak.conf

/usr/bin/expect << EOF
set timeout 2
spawn saslpasswd2 -a libvirt admin -f /etc/libvirt/passwd.db
expect "assword:" {send "admin\r"}
expect "(for verification)" {send "admin\r"}
expect eof
EOF
sed -i '/#listen_addr = /clisten_addr = "0.0.0.0"'  /etc/libvirt/libvirtd.conf
sed -i 's/#listen_tls = 0/listen_tls = 1/g' /etc/libvirt/libvirtd.conf
sed -i 's/#listen_tcp = 0/listen_tcp = 0/g' /etc/libvirt/libvirtd.conf
sed -i '/#auth_tls =/cauth_tls = "sasl"' /etc/libvirt/libvirtd.conf
sed -i 's/#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/g' /etc/sysconfig/libvirtd
sed -i 's/#vnc_listen/vnc_listen/g' /etc/libvirt/qemu.conf


cp /etc/sasl2/libvirt.conf /etc/sasl2/libvirt-bak.conf
sed -i 's/^mech_list: gssapi/#mech_list: gssapi/g' /etc/sasl2/libvirt.conf
sed -i 's/^#mech_list: scram-sha-1$/mech_list: scram-sha-1/g' /etc/sasl2/libvirt.conf
sed -i 's|^keytab: /etc/libvirt/krb5.tab|#keytab: /etc/libvirt/krb5.tab|g' /etc/sasl2/libvirt.conf 
sed -i "s|^#sasldb_path: /etc/libvirt/passwd.db|sasldb_path: /etc/libvirt/passwd.db|g" /etc/sasl2/libvirt.conf 

systemctl restart libvirtd
}

if [[ ! -f /etc/libvirt/.configure_libvirtd ]];then
    message "Start to config libvirtd for KVM..."
    configure_libvirtd
    touch /etc/libvirt/.configure_libvirtd
else
    message "Libvirtd already configured, ignore..."
fi

define_default_bridge()
{
DEFAULT_DEVICE=$(ip -o -4 a | tr -s ' ' | cut -d' ' -f 2 | grep -v -e '^lo[0-9:]*$' | head -1)
DEFAULT_DEVICE_IP=$(ip -o -4 a | tr -s ' ' | cut -d' ' -f 2,4 |grep -v -e '^lo[0-9:]*' | head -1 |cut -d' ' -f 2 | cut -d'/' -f1)
#DEFAULT_DEVICE_GW=$(echo $DEFAULT_DEVICE_IP |  cut -d '.' -f1,2,3)
DEFAULT_DEVICE_GW=$(route -n |grep ^0.0.0.0 | awk '{print $2}')
cat > ifcfg-libvirtmgr <<EOF
TYPE=Bridge
BOOTPROTO=static
NAME=libvirtmgr
DEVICE=libvirtmgr
ONBOOT=yes
IPADDR=$DEFAULT_DEVICE_IP
NETMASK=255.255.255.0
GATEWAY=$DEFAULT_DEVICE_GW
USERCTL=no
DELAY=0
STP=off
MTU=1500
DEFROUTE=yes
NM_CONTROLLED=no
IPV6INIT=yes
IPV6_AUTOCONF=yes
EOF

# need to handle bond interface and normal interface
if [[ -z $(grep -i "TYPE=bond" /etc/sysconfig/network-scripts/ifcfg-$DEFAULT_DEVICE) ]];then
cat > ifcfg-default <<EOF
DEVICE=$DEFAULT_DEVICE
NAME=$DEFAULT_DEVICE
BRIDGE=libvirtmgr
ONBOOT=yes
MTU=1500
DEFROUTE=no
NM_CONTROLLED=no
IPV6INIT=no
EOF
else
cat > ifcfg-default <<EOF
TYPE=bond
BOOTPROTO=none
BONDING_MASTER=yes
NAME=$DEFAULT_DEVICE
DEVICE=$DEFAULT_DEVICE
ONBOOT=yes
BRIDGE=libvirtmgr
MTU=1500
NM_CONTROLLED=no
EOF
grep BONDING_OPTS /etc/sysconfig/network-scripts/ifcfg-$DEFAULT_DEVICE >> ifcfg-default
fi
mv /etc/sysconfig/network-scripts/ifcfg-$DEFAULT_DEVICE /root/ifcfg-$DEFAULT_DEVICE-bak
cp ifcfg-libvirtmgr /etc/sysconfig/network-scripts/ifcfg-libvirtmgr
cp ifcfg-default /etc/sysconfig/network-scripts/ifcfg-$DEFAULT_DEVICE
systemctl restart network
}

if [[ -z $(ip -o a | tr -s ' ' | cut -d' ' -f 2 |grep libvirtmgr) ]];then
    message "Start to define a bridge with name 'libvirtmgr'..."
    define_default_bridge
else
    message "libvirtmgr bridge already exist, ignore...."
fi

define_default_net()
{
cat >libvirtmgr-net.xml<<EOF
<network>
  <name>libvirtmgr-net</name>
  <forward mode='bridge'/>
  <bridge name='libvirtmgr'/>
</network>
EOF
virsh net-define libvirtmgr-net.xml
virsh net-start libvirtmgr-net
virsh net-autostart libvirtmgr-net
}

if [[ -z $(virsh net-list |grep libvirtmgr-net) ]];then
    message "Start to define libvirtmgr net for KVM..."
    define_default_net
else
    message "libvirtmgr net already exist, ignore...."
fi


define_default_pool()
{
poolpath=/data1/kvm

# Please mount extra disk to store vm disks
if [[ ! -d /data1 ]];then
    message "Directory /data1 doesn't exist, please mount it first..."
    exit 1
fi

cat > kvm-pool.xml <<EOF
<pool type='dir'>
  <name>kvm-disk-pool</name>
  <target>
    <path>$poolpath</path>
      <permissions>
        <mode>0777</mode>
        <owner>107</owner>
        <group>107</group>
      <label>kvm default storage pool</label>
    </permissions>
  </target>
</pool>
EOF
mkdir -p $poolpath
virsh pool-define kvm-pool.xml
virsh pool-autostart kvm-disk-pool
virsh pool-start kvm-disk-pool
}


if [[ -z $(virsh pool-list|grep kvm) ]];then
    message "Start to define default pool with name 'kvm'..."
    define_default_pool
else
    message "Default pool already exist, ignore..."
fi

message "Setup finish successfully. Exit."
message "Now you need to config libvit for tls(Encryption & Authentication) for each kvm host, so that you can connect to those host to manage VMs via libvirtd..."
message "For more information, please visit https://wiki.libvirt.org/page/TLSSetup"
exit 0
