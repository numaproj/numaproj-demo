SHELL:=/bin/bash

PACKAGE=quay.io/numaio/numaflow-demo/sentiment-analysis
VERSION?=v0.0.1

.PHONY: image
image:
	docker buildx build -t "$(PACKAGE):$(VERSION)" --platform linux/amd64,linux/arm64 . --push
