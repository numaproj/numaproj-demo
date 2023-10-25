# Numaproj Assist Installation

`Numaproj Assist` is a tool to help you quickly detect if there's any issue with your application. It leverages large language models to analyze the application logs, Kubernetes events and pod running status to identify the root cause of the problem if there's any. The tool is running as an extension in the Argo CD UX.

## Installation

The following steps install `Numaproj Assist` in your Kubernetes cluster, and run a demo application to show how it works.

### Prerequisites

- A Kubernetes cluster
- `kubectl` CLI

### Installation Steps

1. Install Numaflow CRD

```bash
kubectl apply -k https://github.com/numaproj/numaflow/config/advanced-install/minimal-crds?ref=stable
```

2. Install and configure Prometheus if you don't have one

3. Install Argo CD
4. Install Argo CD Extension
5. Install demo app

6. Install `Numaproj Assist` related components

```bash
kubectl apply -k ./numaproj-assist
```
