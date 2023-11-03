SHELL:=/bin/bash

PACKAGE=quay.io/numaio/numaflow-demo/sentiment-analysis
VERSION?=v0.0.1

.PHONY: image
image:
	docker build -t "$(PACKAGE):$(VERSION)" .
