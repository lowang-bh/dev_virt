
## Server setup
### 1. install krb5-server
```
yum install krb5-server krb5-libs
```
### 2. 修改krb5.conf
主要修改libdefaults中default_realm， realms 和domain_realm部分
```
[root@KVM1 ~]# cat /etc/krb5.conf
# Configuration snippets may be placed in this directory as well
includedir /etc/krb5.conf.d/

[logging]
 default = FILE:/var/log/krb5libs.log
 kdc = FILE:/var/log/krb5kdc.log
 admin_server = FILE:/var/log/kadmind.log

[libdefaults]
 dns_lookup_realm = false
 ticket_lifetime = 24h
 renew_lifetime = 7d
 forwardable = true
 rdns = false
 default_realm = KVM1
 default_ccache_name = KEYRING:persistent:%{uid}

[realms]
 KVM1 = {
  kdc = kvm1
  admin_server =kvm1
 }

[domain_realm]
 .kvm1= KVM1
 kvm1 = KVM1
```

### 3. 修改kdc.conf
修改realms部分admin_keytab，将默认的admin_keytab（KDC进行校验的keytab）改成/etc/libvirt/krb5.tab
```
[root@KVM1 ~]# cat /var/kerberos/krb5kdc/kdc.conf
[kdcdefaults]
 kdc_ports = 88
 kdc_tcp_ports = 88

[realms]
 KVM1 = {
  #master_key_type = aes256-cts
  acl_file = /var/kerberos/krb5kdc/kadm5.acl
  dict_file = /usr/share/dict/words
  #admin_keytab = /var/kerberos/krb5kdc/kadm5.keytab
  admin_keytab = /etc/libvirt/krb5.tab
  supported_enctypes = aes256-cts:normal aes128-cts:normal des3-hmac-sha1:normal arcfour-hmac:normal camellia256-cts:normal camellia128-cts:normal des-hmac-sha1:normal des-cbc-md5:normal des-cbc-crc:normal
 }
```
### 4.创建/初始化Kerberos database
其中，[-s]表示生成stash file，并在其中存储master server key（krb5kdc）；还可以用[-r]来指定一个realm name —— 当krb5.conf中定义了多个realm时才是必要的
`kdb5_util create -r KVM1 -s`
创建完成后，会生成如下几个文件
```
[root@KVM1 ~]# ls -la /var/kerberos/krb5kdc/
total 40
drwxr-xr-x. 2 root root  4096 Jun 19 12:10 .
drwxr-xr-x. 4 root root    31 Jun  8 23:12 ..
-rw-------. 1 root root    69 Jun 19 11:38 .k5.KVM1
-rw-------. 1 root root    15 Jun 19 11:58 kadm5.acl
-rw-------. 1 root root   485 Jun 19 12:10 kdc.conf
-rw-------. 1 root root 16384 Jun 19 14:42 principal
-rw-------. 1 root root  8192 Jun 19 11:38 principal.kadm5
-rw-------. 1 root root     0 Jun 19 11:38 principal.kadm5.lock
-rw-------. 1 root root     0 Jun 19 14:42 principal.ok
```
修改kadm5.acl
```
[root@KVM1 krb5kdc]# vim kadm5.acl
  1 */admin@KVM1    *
```
添加管理用户admin/admin和libvirt用户libvirt/kvm1
```
[root@KVM1 ~]# kadmin.local
Authenticating as principal root/admin@KVM1 with password.
kadmin.local:  add_principal libvirt/kvm1
WARNING: no policy specified for libvirt/kvm1@KVM1; defaulting to no policy
Enter password for principal "libvirt/kvm1@KVM1":
Re-enter password for principal "libvirt/kvm1@KVM1":
Principal "libvirt/kvm1@KVM1" created.
kadmin.local:  ktadd -k /etc/libvirt/krb5.tab libvirt/kvm1
Entry for principal libvirt/kvm1 with kvno 2, encryption type aes256-cts-hmac-sha1-96 added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type aes128-cts-hmac-sha1-96 added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type des3-cbc-sha1 added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type arcfour-hmac added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type camellia256-cts-cmac added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type camellia128-cts-cmac added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type des-hmac-sha1 added to keytab WRFILE:/etc/libvirt/krb5.tab.
Entry for principal libvirt/kvm1 with kvno 2, encryption type des-cbc-md5 added to keytab WRFILE:/etc/libvirt/krb5.tab.
kadmin.local:  quit
```
启动服务
```
[root@KVM1 ~]# systemctl start krb5kdc.service
[root@KVM1 ~]# systemctl start kadmin
[root@KVM1 ~]# systemctl enable krb5kdc
Created symlink from /etc/systemd/system/multi-user.target.wants/krb5kdc.service to /usr/lib/systemd/system/krb5kdc.service.
[root@KVM1 ~]# systemctl enable kadmin
Created symlink from /etc/systemd/system/multi-user.target.wants/kadmin.service to /usr/lib/systemd/system/kadmin.service.
```

### 5. 认证用户
```
[root@KVM1 libvirt]# kinit libvirt/kvm1 -k -t /etc/libvirt/krb5.tab
[root@KVM1 libvirt]# klist
Ticket cache: KEYRING:persistent:0:0
Default principal: root/admin@KVM1

Valid starting       Expires              Service principal
06/19/2018 14:38:09  06/20/2018 14:38:09  krbtgt/KVM1@KVM1

[root@KVM1 ~]#  virsh -c qemu+tcp://root@kvm1/system
Welcome to virsh, the virtualization interactive terminal.

Type:  'help' for help with commands
       'quit' to quit

virsh #
```
- 错误解决：如下错误，需要先kinit
```
[root@KVM1 ~]# klist
klist: Credentials cache keyring 'persistent:0:0' not found
```

## Client
install krb5-client
```
yum install krb5-workstation krb5-libs
```
use authconfig to set up the system to use Kerberos
```
authconfig --enablekrb5 --krb5realm=KVM1 --krb5adminserver=kvm1 --krb5kdc=kvm1 --update
```
