# Build a container image on worker
When you edit code other than a worker, you must push a container image to your container registry. In container image size is big, time to push is so longer. To avoid such situations, it is recommended to build the container image on the worker during development

## When using CRI-O in a Kubernetes cluster

- Since you can't use `docker build`, you use `buildah bud` instead.
```
cd numaflow-dra
sudo buildah bud -t [registry_URL]/[project]/dci_poc:debug -f ./path/to/Dockerfile --layers
sudo buildah bud -t [registry_URL]/[project]/dci_poc-gpu:debug -f ./path/to/Dockerfile --layers
sudo buildah images
```


# File Explanation
- 2-even-odd-pipeline-for-dra.yaml
    - Update numaflow official manifest file and verify GPU is assigned to a pod.
- sample-single-gpu-01.yaml
    - Update DRA official manifest file and verify whether there is a problem in contaier images.
- pipeline-debug.yaml
    - A manifest file for debugging that use a image on worker node.
