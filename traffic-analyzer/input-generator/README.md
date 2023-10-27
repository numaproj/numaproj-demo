### INPUT GENERATOR

The input generator is a simple application that generates random traffic data and sends it to a Kafka topic.
It generates data for every 10 milliseconds.

Steps to run the input generator:

* Deploy Kafka
```yaml
kubectl apply -f manifests/kafka-minimal.yaml
```

* Deploy the input generator
```yaml
kubectl apply -f manifests/deloyment.yaml
```