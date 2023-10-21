# Numalogic Demo Application

This repo contains the demo app (featuring fishes) that can be used to demonstrate the power of Numaproj. The same demo 
app has been demoed in [Kubecon](https://www.youtube.com/watch?v=-YGS1hmd60E) and in [ArgoCon](https://www.youtube.com/watch?v=_pRJ0_yzxNs).

![img](ui/assets/images/demo.png)

To run just the demo app

```bash
make run
```

To run an end-to-end example:

Apply the manifests of one of the examples:

```bash
kustomize build ./manifests | kubectl apply -f -
```

## Containers

Available fish containers are: octo, puffy, (e.g. `quay.io/numaio/numalogic-demo:octo`). Also available are:
* High error rate container, prefixed with the word `error` (e.g. `quay.io/numaio/numalogic-demo:puffyerror`)
* High latency container, prefixed with the word `slow` (e.g. `quay.io/numaio/numalogic-demo:puffylatency`)


## Releasing

To release new images:

```bash
make release IMAGE_NAMESPACE=argoproj DOCKER_PUSH=true
```
