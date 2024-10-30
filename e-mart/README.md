# e-mart

This is a simple project to demonstrate how to use the [Numaflow](https://github.com/numaproj/numaflow) to analyze the order information of an e-commerce platform.

## Overview

The demo project simulates an e-commerce platform, it keeps generating order information, and streaming to a Kafka topic. A Numaflow pipeline is used to analyze the order information, enrich the data with product information, prices, flatmap the order to multiple messages in different categories, and then aggregate the data to calculate the sold products and the total revenue of each category every N seconds. In the end, the aggregated data is sent to some other data sinks.

A optinal Grafana sink is also used to visualize the data, otherwise the data can be visualized by the log sink in console logs.

The original order information looks like this:

```json
{
  "id": "order-1730269550331762000-762",
  "order_time": "2024-10-29T23:25:50-07:00",
  "items": [
    {
      "product_id": "p-006-0005",
      "quantity": 2
    },
    {
      "product_id": "p-005-0003",
      "quantity": 1
    },
    {
      "product_id": "p-002-0007",
      "quantity": 2
    },
    {
      "product_id": "p-002-0004",
      "quantity": 1
    }
  ]
}
```

After enrichment in the map operation, some properties are added to the original data, and flatmap to multiple messages:

```json
// Message 1
{
  "order_id": "order-1730318669701322420-175",
  "order_time": "2024-10-30T20:04:29Z",
  "category_id": "cate-007",                                                   -- Added
  "category_name": "Men's Shoes",                                              -- Added
  "items": [
    {
      "product_id": "p-007-0001",
      "name": "HEYDUDE Wally Stretch - Mens Comfortable Slip on Shoes",        -- Added
      "quantity": 1,
      "price": 23.99
    },
    {
      "product_id": "p-007-0005",
      "name": "Vans Mountain Mule Slip On Casual Shoe",                        -- Added
      "quantity": 1,
      "price": 31.49
    }
  ]
}
```

```json
// Message 2
{
  "order_id": "order-1730318669701322420-175",
  "order_time": "2024-10-30T20:04:29Z",
  "category_id": "cate-005",                                                   -- Added
  "category_name": "Sports Goods",                                             -- Added
  "items": [
    {
      "product_id": "p-005-0006",
      "name": "6180Lbs Breaking Strength Bull Rope 1/2Inch Diameter",          -- Added
      "quantity": 1,
      "price": 30.44
    }
  ]
}
```

```json
// Message 3
{
  "order_id": "order-1730318669701322420-175",
  "order_time": "2024-10-30T20:04:29Z",
  "category_id": "cate-002",                                                   -- Added
  "category_name": "Men's Clothing",                                           -- Added
  "items": [
    {
      "product_id": "p-002-0006",
      "name": "Men's Pure Mink Cashmere Turtleneck Sweater Long-sleeved",      -- Added
      "quantity": 1,
      "price": 35.99
    }
  ]
}
```

In the end, the aggregated data looks like below (group by category every 60 seconds):

```json
{
  "start": "2024-10-30T20:01:00Z",
  "end": "2024-10-30T20:02:00Z",
  "category_id": "cate-003",
  "category_name": "Health & Beauty",
  "item_count": 28,
  "total_amount": 472.41
}
```

```json
{
  "start": "2024-10-30T20:01:00Z",
  "end": "2024-10-30T20:02:00Z",
  "category_id": "cate-005",
  "category_name": "Sports Goods",
  "order_count": 62,
  "total_amount": 638.91
}
```

## Pipeline

![Pipeline Topology](pipeline-topology.png)

## Installation

To run the demo project, you need to have a Kubernetes cluster and the `kubectl` command line tool installed. Then you can install the project by running the following commands.

```bash
# Install Numaflow if you haven't
kubectl create ns numaflow-system
kubectl apply -n numaflow-system -f https://github.com/numaproj/numaflow/releases/download/v1.3.3/install.yaml

# Install the ISB Service
kubectl apply -f https://raw.githubusercontent.com/numaproj/numaflow/stable/examples/0-isbsvc-jetstream.yaml

# Install a Kafka service
kubectl apply -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/emart/manifests/kafka.yaml

# Install the order info generator
kubectl apply -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/emart/manifests/emart-order-gen.yaml

# Install the data analysis pipeline without Grafana sink
kubectl apply -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/emart/manifests/pipeline.yaml

# Install the Grafana
# TODO

# Grafana config
# TODO

# Install the data analysis pipeline with Grafana sink
kubectl apply -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/emart/manifests/pipeline-w-grafana-sink.yaml
```

## UI

```bash
kubectl -n numaflow-system port-forward svc/numaflow-server 8443
```

Access the UI at https://localhost:8443 to see the pipeline running.

## Cleanup

```bash
kubectl delete -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/dooreats/manifests/pipeline.yaml
kubectl delete -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/dooreats/manifests/order-gen.yaml
kubectl delete -f https://raw.githubusercontent.com/numaproj/numaproj-demo/main/dooreats/manifests/kafka.yaml
kubectl delete -f https://raw.githubusercontent.com/numaproj/numaflow/stable/examples/0-isbsvc-jetstream.yaml
kubectl delete -n numaflow-system -f https://github.com/numaproj/numaflow/releases/download/v1.3.3/install.yaml
kubectl delete ns numaflow-system
```
