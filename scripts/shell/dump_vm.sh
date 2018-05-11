#!bin/bash

JSON="./conf.json"

DB_HOST=$(jq .common_conf.db_conf $JSON|sed 's/"//g')
export DB_HOST=$DB_HOST
VIRTPLATFORM_PATH=$(jq .common_conf.virtplatform_path $JSON|sed 's/"//g')
export PYTHONPATH=$PYTHONPATH:$VIRTPLATFORM_PATH

HOST=$(jq .common_conf.hostip $JSON|sed 's/"//g')
USER=$(jq .common_conf.user $JSON|sed 's/"//g')
PASSWD=$(jq .common_conf.passwd $JSON|sed 's/"//g')
VMNAME=$(jq .dump_vm.vmname $JSON|sed 's/"//g')

echo "python ../dump_vm.py --host=$HOST -u $USER -p ****** $VMNAME"
python ../dump_vm.py --host=$HOST -u $USER -p $PASSWD $VMNAME
