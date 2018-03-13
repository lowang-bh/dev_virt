#!/usr/bin/env bash
#########################################################################
# File Name: xenserver_yum_config.sh
# Author: longhui
# Created Time: 2018-03-13 10:54:42
#########################################################################
set -e
BASEDIR=/root

#1.install lib and make python27
yum -yq install make gcc
echo "Successfully install make&&gcc"
yum -yq install openssl openssl-devel openssl-static
echo "Successfully installed openssl"
yum -yq install sqlite-devel
yum -yq install bzip2-devel bzip2-libs
yum -yq install readline readline-devel readline-static
echo "Successfully installed all pakage to make  python27"

cd $BASEDIR
tar xf Python-2.7.6.tar
cd Python-2.7.6/ && ./configure --prefix=/usr/local/python
make && make install

cd $BASEDIR
unzip setuptools-38.5.1.zip
cd setuptools-38.5.1/ && /usr/local/python/bin/python setup.py install

cd $BASEDIR
tar zxf pip-9.0.1.tar.gz
cd pip-9.0.1/ && /usr/local/python/bin/python setup.py install
/usr/local/python/bin/pip install virtualenv

cd $BASEDIR
/usr/local/python/bin/virtualenv -p /usr/local/python/bin/python python27
source python27/bin/activate && pip install xenapi
pip install six
pip install ipaddress
#sed -i "/PYTHONPATH/s/$/:\/root\/python27\/dev_xen" python27/bin/activate
sed -i '/^export PATH/a\export PYTHONPATH=$PYTHONPATH:/root/python27/dev_xen' python27/bin/activate

echo "Env setup successfully."


