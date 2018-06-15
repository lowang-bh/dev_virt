#!/usr/bin/env bash

systemctl stop firewalld
systemctl disable firewalld

setenforce 0
cp /etc/sysconfig/selinux /etc/sysconfig/selinux.bak
sed -i '/^SELINUX=/cSELINUX=disabled' /etc/sysconfig/selinux
cp /etc/selinux/config /etc/selinux/config.bak
sed -i "s/#\{0,1\}SELINUX=enforcing/SELINUX=disabled/" /etc/selinux/config
yum -y install etcd kubernetes

#sed -i '/^ETCD_LISTEN_CLIENT_URLS=/cETCD_LISTEN_CLIENT_URLS=\"http://0.0.0.0:2379\"' /etc/etcd/etcd.conf

hostname=$(hostname)
master_name=k8s-1

# setup master
# if a error about: No API token found for service account "default", retry after the token is automatically created and added to the service account
# change the KUBE_ADMISSION_CONTROL="
if [[ $hostname == $master_name ]];then
    mv /etc/etcd/etcd.conf /etc/etcd/etcd.conf.bak
    echo 'ETCD_NAME="default"' >> /etc/etcd/etcd.conf
    echo 'ETCD_DATA_DIR="/var/lib/etcd/default.etcd"' >> /etc/etcd/etcd.conf
    echo 'ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"' >> /etc/etcd/etcd.conf
    echo 'ETCD_ADVERTISE_CLIENT_URLS="http://localhost:2379"' >> /etc/etcd/etcd.conf

    mv /etc/kubernetes/config  /etc/kubernetes/config.bak
    echo 'KUBE_LOGTOSTDERR="--logtostderr=true"' >> /etc/kubernetes/config
    echo 'KUBE_LOG_LEVEL="--v=0"' >> /etc/kubernetes/config
    echo 'KUBE_ALLOW_PRIV="--allow-privileged=false"' >> /etc/kubernetes/config
    echo "KUBE_MASTER=\"--master=http://$master_name:8080\"" >> /etc/kubernetes/config

    mv /etc/kubernetes/apiserver /etc/kubernetes/apiserver.bak
    echo 'KUBE_API_ADDRESS="--address=0.0.0.0"' >> /etc/kubernetes/apiserver
    echo 'KUBE_API_PORT="--port=8080"' >>  /etc/kubernetes/apiserver
    echo 'KUBELET_PORT="--kubelet-port=10250"' >> /etc/kubernetes/apiserver
    echo "KUBE_ETCD_SERVERS=\"--etcd-servers=http://$master_name:2379\"">> /etc/kubernetes/apiserver
    echo 'KUBE_SERVICE_ADDRESSES="--service-cluster-ip-range=10.254.0.0/16"' >> /etc/kubernetes/apiserver
    echo 'KUBE_ADMISSION_CONTROL="--admission-control=NamespaceLifecycle,NamespaceExists,LimitRanger,SecurityContextDeny,ServiceAccount,ResourceQuota"' >> /etc/kubernetes/apiserver
    echo 'KUBE_API_ARGS=""' >> /etc/kubernetes/apiserver

    for SERVICES in etcd kube-apiserver kube-controller-manager kube-scheduler;
    do
        systemctl restart $SERVICES
        systemctl enable $SERVICES
        systemctl status $SERVICES
    done
    # print the nodes list
    kubectl get nodes
fi

# setup nodes, treat master as one node
#if thereis a error: details: (open /etc/docker/certs.d/registry.access.redhat.com/redhat-ca.crt: no such file or directory)",then comment the KUBELET_POD_INFRA_CONTAINER
mv /etc/kubernetes/kubelet /etc/kubernetes/kubelet.bak
echo 'KUBELET_ADDRESS="--address=0.0.0.0"' >> /etc/kubernetes/kubelet
echo "KUBELET_HOSTNAME=\"--hostname-override=$hostname\"" >> /etc/kubernetes/kubelet
echo "KUBELET_API_SERVER=\"--api-servers=http://$master_name:8080\"" >> /etc/kubernetes/kubelet
echo 'KUBELET_POD_INFRA_CONTAINER="--pod-infra-container-image=registry.access.redhat.com/rhel7/pod-infrastructure:latest"' >> /etc/kubernetes/kubelet
echo 'KUBELET_ARGS=""' >> /etc/kubernetes/kubelet

#for SERVICES in flanneld kube-proxy kubelet docker;
# k8s-2
for SERVICES in kube-proxy kubelet docker;
do
    systemctl restart $SERVICES
    systemctl enable $SERVICES
    systemctl status $SERVICES
done
#  kubectl create  -f pod.yaml
#  kubectl get pods
#  kubectl describe pod/rss-site
#
