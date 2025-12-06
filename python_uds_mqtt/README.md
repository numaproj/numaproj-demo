# Python MQTT User-Defined Source for Numaflow

This User-Defined Source connects to an MQTT broker, subscribes to a topic, and emits messages into a Numaflow pipeline.

## Usage

### Configuration

Set environment variables to configure the MQTT connection:

| Variable      | Description                | Default     |
| ------------- | -------------------------- | ----------- |
| `MQTT_BROKER` | MQTT broker hostname       | `localhost` |
| `MQTT_PORT`   | MQTT broker port           | `1883`      |
| `MQTT_TOPIC`  | MQTT topic to subscribe to | `test`      |

## Development

### Requirements

```bash
pip install -r requirements.txt
```

- Python 3.12+
- pynumaflow >= 0.8.0
- aiomqtt >= 2.0.0

### Build

```bash
docker build -t mqtt-udsource:latest .
```

### Local Testing

Helps verify MQTT connection. 

**Prerequisites:**
```bash
# Install mosquitto clients 
brew install mosquitto
```

```bash
# Terminal 1: Start MQTT broker (if not already running)
docker run -d --name mosquitto-test -p 1883:1883 eclipse-mosquitto mosquitto -c /mosquitto-no-auth.conf

# Terminal 2: Run the Python MQTT source
python3 mqtt_udsource.py

# Terminal 3: Subscribe to verify and view messages
mosquitto_sub -h localhost -p 1883 -t test -v

# Terminal 4: Publish test messages
mosquitto_pub -h localhost -p 1883 -t test -m 'Hello from MQTT!'


## Deploying in Kubernetes

```bash
# Create namespace
kubectl create namespace numaflow-demo

# Create ISB service
kubectl apply -f manifests/isbsvc.yaml -n numaflow-demo

# Build container and load into cluster (using kind)
docker build -t mqtt-udsource:latest .
kind load docker-image mqtt-udsource:latest --name kind

# Deploy MQTT broker
kubectl apply -f manifests/mosquitto-deployment.yaml -n numaflow-demo
kubectl wait --for=condition=Ready pods -l app=mosquitto -n numaflow-demo --timeout=120s

# Deploy pipeline
kubectl apply -f manifests/pipeline.yaml -n numaflow-demo
kubectl wait --for=condition=Ready pods -l numaflow.numaproj.io/vertex-name=mqtt-source -n numaflow-demo --timeout=120s
```

## Sending Test Messages to the MQTT Broker

After deploying the MQTT broker and pipeline, you can publish test messages from inside the Kubernetes cluster or locally.

### 1. Publish from Inside K8s cluster

```bash
# Find Mosquitto pod
MOSQUITTO_POD=$(kubectl get pods -n numaflow-demo -l app=mosquitto -o jsonpath='{.items[0].metadata.name}')

# Send a test message
kubectl exec -n numaflow-demo $MOSQUITTO_POD -- \
  mosquitto_pub -h localhost -t test -m "Hello from Kubernetes"
```

### 2. Publish from Your Local Machine (via port-forward)

```bash
# Terminal 1: Port-forward the MQTT broker
kubectl port-forward -n numaflow-demo svc/mosquitto-service 1883:1883

# Terminal 2: Publish from your machine
mosquitto_pub -h localhost -t test -m "Hello from local machine"
```

### View Pipeline Output

```bash
# Check MQTT source logs and sink output
kubectl logs -n numaflow-demo -l numaflow.numaproj.io/vertex-name=mqtt-source -c udsource --tail=20
kubectl logs -n numaflow-demo -l numaflow.numaproj.io/vertex-name=log-sink --all-containers --tail=20

```

## Files

- `mqtt_udsource.py` - Source implementation
- `Dockerfile` - Container image definition
- `requirements.txt` - Python dependencies
- `manifests/` - Manifests for deploying using Kubernetes
  - `pipeline.yaml` - Example Numaflow pipeline
  - `mosquitto-deployment.yaml` - Test MQTT broker deployment
  - `isbsvc.yaml` - Example InterStepBufferService configuration