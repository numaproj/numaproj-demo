# Numaproj Assist Demo

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

2. Install Prometheus if you don't have one, and configure
   

2.1. Configure the Prometheus Rule for AIOps (Please update the your Prometheus namespace)
```bash
kubectl apply -n monitoring -f https://github.com/numaproj/numalogic-prometheus/blob/main/manifests/prerequisites/prometheus/prometheus-rules.yaml
```
   

4. Install Argo CD and Argo rollouts
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml


```
4. Install ArgoCD Metrics Server
```base
kubectl -n argocd -k https://github.com/argoproj-labs/argocd-extension-metrics/manifests?ref=main
```
5. Install AIOps Anomaly pipeline
```base
kubectl  -k https://raw.githubusercontent.com/numaproj/numalogic-prometheus/main/manifests/pipeline/install-numalogic-rollouts.yaml
```


6. Install ArgoCD Extension
```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/manifests/numaproj-assist/argocd-extn/argocd-extn-configmap.yaml
kubectl apply -n argocd -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/manifests/numaproj-assist/argocd-extn/argocd-extn-server-cm.yaml
kubectl patch deployment argocd-server --patch-file https://raw.githubusercontent.com/numaproj/numaproj-demo/main/manifests/numaproj-assist/argocd-extn/argocd-deployment-patch-numaproj-assist.yaml
```

7. Install demo app
  a. Create argocd application 
  b. Point the manifest to `https://github.com/numaproj/numaproj-demo/tree/main/demo-app/manifests/rollout`

8. Install `Numaproj Assist` related components

```bash
kubectl apply -k ./manifests/numaproj-assist
```


9. Install ArgoCD numaproj Assist Backend server
```base
kubectl apply -n numaproj-assist https://raw.githubusercontent.com/numaproj-labs/argocd-extn-numaproj-assist/main/manifests/install.yaml
```

## Demo
