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
```bash
kubectl apply -f  https://raw.githubusercontent.com/numaproj/numalogic-prometheus/main/manifests/prerequisites/prometheus/install.yaml
```

2.1. [skip if you did step 2] Configure the Prometheus Rule for AIOps (Please update the your Prometheus namespace)
```bash
kubectl apply -n monitoring -f https://github.com/numaproj/numalogic-prometheus/blob/main/manifests/prerequisites/prometheus/prometheus-rules.yaml
```
   

3. Install Argo CD and Argo rollouts
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml


```
4. Install ArgoCD Metrics Server
```base
kubectl -n argocd apply -k https://github.com/argoproj-labs/argocd-extension-metrics/manifests?ref=main
```
5. Install AIOps Anomaly pipeline
```base
kubectl  apply -f https://raw.githubusercontent.com/numaproj/numalogic-prometheus/main/manifests/pipeline/install-numalogic-rollouts.yaml -n numalogic-rollouts
```


6. Install ArgoCD Extension
```bash
kubectl apply -n argocd -f ./manifests/numaproj-assist/argocd-extn/argocd-extn-configmap.yaml
kubectl apply -n argocd -f ./manifests/numaproj-assist/argocd-extn/argocd-extn-server-cm.yaml
kubectl apply -n argocd -f ./manifests/numaproj-assist/argocd-extn/argocd-rbac-cm.yaml
kubectl patch deployment argocd-server -n argocd --patch-file ./manifests/numaproj-assist/argocd-extn/argocd-deployment-patch-numaproj-assist.yaml
```

7. Install demo app
  a. Create argocd application 
   ```bash
    kubectl apply -n argocd -f  ./manifests/numaproj-assist/argocd-app/argocd-demo-app-application.yaml
    ```
  b. Port forward argocd UI
  ```bash
  kubectl -n argocd port-forward svc/argocd-server 8080:80
  ```
  c. open the browser "https://localhost:8080/"
  username is `admin`
  To get password execute below command
  ```
  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
  ```

8. Install `Numaproj Assist` related components

```bash
kubectl create ns numaproj-assist

# Create a Kubernetes secret for the openai api key (replace <openai-api-key> before running the following command).
```bash
kubectl -n numaproj-assist create secret generic log-summarization-tokens --from-literal=openai-api-key='<openai-api-key>'

kubectl apply -k ./manifests/numaproj-assist
```

9. Install ArgoCD numaproj Assist Backend server
```base
kubectl apply -n numaproj-assist -f https://raw.githubusercontent.com/numaproj-labs/argocd-extn-numaproj-assist/main/manifests/install.yaml
```
10. Open demo App
```bash
   kubectl port-forward svc/numalogic-demo-service 8081:8080 -n rollout-numalogic-demo
```
open the browser "https://localhost:8081/"
## Demo
