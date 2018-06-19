# libvirtd auth with tls
libvirtd使用tls进行认证需要为client端和server端颁发证书，严格来说，每一台client和server都应该有一个独立的证书，由CA颁发。
CA可以通过自己建立而不使用商业版CA。详细的clent和server分别独立颁发一份证书的过程，参考libvirtd文档，写的很细。

[TLSSetup](https://wiki.libvirt.org/page/TLSSetup)

### 1. libvirtd.conf 需要打开tls监听和tls认证sasl
```
listen_tls = 1
auth_tls = "sasl"
```
### 2. /etc/sasl2/libvirt.conf
```
mech_list: scram-sha-1
```
### 3. 为libvirtd添加可以登录的用户名密码
```
[root@kvmhost2 ~]# saslpasswd2 -a libvirt admin
Password:
Again (for verification):
```

# 只颁发一套证书的办法
下面的方法为所有client使用一套证书，所有server使用一套证书，和前面的原理一样，这种方法缺点是不能每一个server都使用hostname连接，只能使
用IP进行连接。
1. 生成CA的cacert.pem，并拷贝到所有clients和servers
2. 生成server的证书，使用的模板server.info里面需要填写所有server的IP，并拷贝到所有servers
3. 生成client的证书，并拷贝到所有clients


```
#!/usr/bin/env bash

yum -y install cyrus-sasl-plain cyrus-sasl-scram cyrus-sasl-lib cyrus-sasl-devel cyrus-sasl-gssapi cyrus-sasl

cat >ca.info <<EOF
cn = libvirt.org
ca
cert_signing_key
EOF

servername=KVMServers
# (CN) field would contain the hostname of the server
# and would match the hostname used in the URI that clients pass to libvirt
# if clients will be connecting to the server using a URI of qemu://compute1.libvirt.org/system,
# so the CN must be "compute1.libvirt.org".
# If clients are likely to connect to the server by IP address,
# then one or more 'ip_address' fields should also be added.
cat > server.info <<EOF
organization = libvirt.org
cn = $servername
ip_address = 10.143.248.100
ip_address = 10.143.248.249
ip_address = 10.143.248.15
tls_www_server
encryption_key
signing_key
EOF

clientname=KVMClient
cat > client.info <<EOF
country = CN
state = Beijing
locality = Beijing
organization = libvirt.org
cn = $clientname
tls_www_client
encryption_key
signing_key
EOF

ips="10.143.248.100 10.143.248.15 10.143.248.249"
#/etc/pki/CA/cacert.pem on all clients and servers
certtool --generate-privkey > cakey.pem
certtool --generate-self-signed --load-privkey cakey.pem --template ca.info --outfile cacert.pem
for ip in $ips
do
    scp cacert.pem root@$ip:/etc/pki/CA/cacert.pem
done

# (CN) field would contain the hostname of the server and would match the hostname used in the URI that clients pass to libvirt
certtool --generate-privkey > serverkey.pem
certtool --generate-certificate --load-privkey serverkey.pem --load-ca-certificate cacert.pem --load-ca-privkey cakey.pem --template server.info --outfile servercert.pem
for ip in $ips
do
    cp serverkey.pem   /etc/pki/libvirt/private/
    cp servercert.pem /etc/pki/libvirt/
done

certtool --generate-privkey > clientkey.pem
certtool --generate-certificate --load-privkey clientkey.pem  --load-ca-certificate cacert.pem --load-ca-privkey cakey.pem --template client.info --outfile clientcert.pem
for ip in $ips
do
    cp clientkey.pem /etc/pki/libvirt/private/clientkey.pem
    cp clientcert.pem /etc/pki/libvirt/clientcert.pem
done
```
