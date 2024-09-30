# serving-demo
Demo project for Numaflow serving

## Steps to Run the Ascii Art Serving Demo

### Step 1: Create local cluster

Choose either K3D or Kind.

#### Create K3D local cluster
```shell
# k3d
k3d cluster create

```

#### Create Kind local cluster
```shell
# kind
kind create cluster
```

### Step 2: Setup Numaflow

#### Step 2.a Checkout Numaflow

```shell
git clone https://github.com/numaproj/numaflow.git # if you haven't already cloned the repo
cd numaflow
git checkout main
make start
```

#### Step 2.b Deploy ISB

```shell
kubectl apply -f examples/0-isbsvc-jetstream.yaml
```

### Step 3: Clone the numaproj-demo repo

```shell
git clone https:://github.com/numaproj/numaproj-demo.git
cd numaproj-demo/serving-demo
```

### Step 4: Create Redis 

```shell
kubectl apply -f manifests/redis-minimal.yaml
```


### Step 5: Build and import images
```shell
make ascii-image
make servesink-image

# import to k3d cluster
k3d image import ascii:0.1
k3d image import servesink:0.1

# import to kind cluster
kind load docker-image ascii:0.1
kind load docker-image servesink:0.1
```

### Step 6: Create Serving Pipeline

```shell
kubectl apply -f manifests/pipeline.yaml
```

### Step 7: Port Forward the Input Pod

```shell
kubectl port-forward ascii-art-pipeline-in-0-xxx 8443
```

### Step 8: Send Curl Requests to Verify Things are Working

#### image to ascii
```shell
curl -H "X-Numaflow-Id: $(uuidgen)" -H 'Content-Type: image/png' -XPOST -T ascii/udfs/assets/numa-512.png -k https://localhost:8443/v1/process/sync_serve
```

#### generate ascii images
```shell
curl -L -k 'https://localhost:8443/v1/process/sync_serve' \
-H "X-Numaflow-Id: $(uuidgen)" \
-H 'Content-Type: application/json' \
-d '{
   "animals": [
       "tiger",
       "dog",
       "elephant"
   ]
}'
```

#### Send Invalid Request to Verify Error Responses

```shell
curl -H "X-Numaflow-Id: $(uuidgen)" -H 'Content-Type: text/plain' -X POST -d "test-$(date +'%s')" -k https://localhost:8443/v1/process/sync_serve
```

```shell
curl -L -k 'https://localhost:8443/v1/process/sync_serve' \
-H "X-Numaflow-Id: $(uuidgen)" \
-H 'Content-Type: application/json' \
-d '{
   "animals": [
       "cat",
       "dog",
       "elephant"
   ]
}'
```
