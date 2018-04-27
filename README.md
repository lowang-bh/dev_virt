ReadME

1. If run these scripts on Xenserver, please first configure the env for xenserver
    with the scripts initial_env.sh
2. If run those scripts locally, please specify an host IP and user/password with:
    --host=HOST --user=USER --pwd=PASSWD

## Env Setting Up:

    1). create a virtual env with python2.7

        virtualenv -p python2 venv
    2). add current dirctory to PYTHONPATH

    3). install pip requirements

        source venv/bin/activate && pip install -r requirements.txt

    4). set up the DB_HOST, eg: example.com or 127.0.0.1:8000 for localhost test

        export DB_HOST=127.0.0.1:8000

    5). Log server is available to write the debug and exception infor to /var/log/virt.log. Remember to use sudo when
        start the log server in case of no permission to the directory /var/log

        sudo nohup python /Users/wang/mygit/dev_xen/lib/Log/logging_server.py &

## Some phrase:
- PIF: physical interface, the eth on server
- VIF: virtual  interface, the eth on VM
- SR:  storage repository, the storage pool on server

# Scripts:

## 1. Sync information from exist server to database

   - `sync_server_info.py`          will sync both server and VM information to DB, and create a record in DB if not exist
   - `sync_server_info.py --update` Just update information to DB

## 2. create_vm.py

  - `--list-vm`             List all the vms in server.
  - `--list-templ`          List all the templates in the server.
  - `--list-network`        List the bridge/switch network in the host

#####  1). <b>**Create a new VM with a template:**<b>
  - `-c VM_NAME, --create=VM_NAME`                        Create a new VM with a template.
  - `-t TEMPLATE, --templ=TEMPLATE`                       Template used to create a new VM.
    
    > create_vm.py -c "test_vm" -t "CentOS 7.2 for Lain"

#####  2). <b>**Create a new VM with a given IP: if a IP specified**<b>
  - `--vif=VIF_INDEX`      The index of virtual interface on which configure will be
  - `--device=DEVICE`      The target physic NIC name with an associated network VIF attach(ed) to
  - `--network=NETWORK`    The target bridge/switch network which VIF connect(ed) to
  - `--ip=VIF_IP`          The ip assigned to the virtual interface

    **a VIF index(*--vif*) is needed and a PIF name(*--device*) or a bridge name(*--network*) is needed**
    > create_vm.py -c "test2" -t "CentOS 7.2 template" --ip=192.168.1.100 --vif=0 --device=eth0

    > create_vm.py -c "test2" -t "CentOS 7.2 template" --ip=192.168.1.100 --vif=0 --network="xapi0"

    **neither *--device* nor *--network*, the default manage network will be used**
    > create_vm.py -c "test2" -t "CentOS 7.2 template" --ip=192.168.1.100 --vif=0

#####  3). <b>**Create a new VM with given max cpu cores:**<b>
  - `--cpu-max=MAX_CORES`   Config the max VCPU cores.
    
    > create_vm.py -c "test2" -t "CentOS 7.2 template" --cpu-max=2

    The max cpu cores can be configured when VM is power off only, and it affect the upper limit when set the cpu cores lively

#####  4). <b>**Create a new VM with memory size:**<b>
  - `--memory=MEMORY_SIZE`  Config the target memory size in GB.
  - `--min-mem=MIN_MEMORY`  Config the min static memory size in GB.
  - `--max-mem=MAX_MEMORY`  Config the max static memory size in GB.

     <b>There are static memory and dynamic memory. The static memory can be set only when VM is power off, and dynamic memory
  can be set when VM is running or stop. Memory limits must satisfy: *min_static_memory <= min_dynamic_memory <= max_dynamic_memory <= max_static_memory*. The max_static_memory will affect the upper limit when set the dynamic memory lively when VM is running.<b>


  - `--memory will set the min dynamic memory and max dynamic memory to the target one, when VM power on, it runs at that memory size`
  - `--min-mem will set the min static memory `
  - `--max-mem will set the max static memory `
    > create_vm.py -c "test2" -t "CentOS 7.2 template" --memory=2 --max-mem=4


## 4. config_vm.py
#### The IP and memory configuration is same as that in create VM.
  - `--list-vif`            List the virtual interface device in guest VM
  - `--list-pif`            List the interface device in the host
  - `--list-network`        List the bridge/switch network in the host
  - `--list-SR`             List the storage repository information in the host

##### 1). <b>**Config a VM's interface, add a VIF, delete a VIF, config a VIF(will delete old one if exist, otherwise create it newly), and the *--ip*, *--device*, *--network* is same as that when create vm**<b>
  - `--add-vif=ADD_INDEX`   Add a virtual interface device to guest VM
  - `--del-vif=DEL_INDEX`   Delete a virtual interface device from guest VM
  - `--vif=VIF_INDEX`      Configure on a virtual interface device

    > config_vm.py "test1"  --vif=0 --ip=192.168.1.200 --device=eth0

    > config_vm.py "test1"  --add-vif=1 --dev=eth1 --ip=192.168.1.200 --netmask=255.255.255.0

##### 2). <b>**config a VM' cpu when it is running**<b>
  - `--cpu-cores=CPU_CORES` Config the VCPU cores lively
      
      > config_vm.py "test1" --cpu-core=4

##### 3). <b>**config a VM' memory when it is running**<b>
  - `--memory=MEMORY_SIZE`  Config the target memory size in GB.
    
    > config_vm.py "test1" --memory=1

##### 4).Add new disk to VM, the storage_name is choosed from *--list-SR*
  - `--add-disk=DISK_SIZE`  The disk size(GB) add to the VM
  - `--storage=STORAGE_NAME` The storage location where the virtual disk put
    > config_vm.py "test1"--add-disk=2 --storage=data2

    **if no *--storage*, will use the storage which has a largest free volume**
    > config_vm.py "test1"--add-disk=2


## 5. power_on.py, power_off.py
 - power_on.py vm1 vm2 \[--host=ip --user=user --pwd=passwd\]
 - power_off.py vm1 vm2 \[--host=ip --user=user --pwd=passwd\]

## 6. dump_vm.py, ist the memory, CPU, Disk, and system information of VM
  - `--list`                List the cpu and memory information
  - `--list-disk`           List the virtual disk size
  - `--list-vifs`           List all the VIFs information

    **if no options, will list all basic informations, include, cpu, memory, os, disk, interface mac and IP**

    **Note: a problem is that the VIF index given to xenserver, but it is not always the index of eth in VM guest, it depend on the create sequence of virtual interface.**

## 7. dump_host.py, list the memory, CPU, Disk, and system information of server
  - dump_host.py    \[--host=ip --user=user --pwd=passwd\]
  - dump_host.py --list-sr \[--host=ip --user=user --pwd=passwd\]
