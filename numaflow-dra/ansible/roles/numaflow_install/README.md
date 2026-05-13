# numaflow_install role

Does the following.

- Installs [Numaflow](https://numaflow.numaproj.io/operations/installation/#cluster-scope)
- Installs the [local static provisioner](https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner) to manage persistent volumes (PVs).
- Creates 3 PVs for an inter-step buffer service (ISBSVC).
- Deploys an ISBSVC. Three pods will be created per ISBSVC.
