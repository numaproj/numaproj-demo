# calico role

Installs Calico, following the steps describe in the section &quot;[Install Calico with Kubernetes API datastore, 50 nodes or less](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises#install-calico-with-kubernetes-api-datastore-50-nodes-or-less)&quot; in the official documentation. There is no need to edit CALICO_IPV4POOL_CIDR in calico.yaml because Calico installed by this role will use the CIDR block provided via `kubeadm init --pod-network-cidr` (and it is defined in `vars-stg.yml`).
