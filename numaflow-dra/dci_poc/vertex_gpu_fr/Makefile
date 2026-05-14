include ./../../repo.env

# To source (.) ../../opencv-cuda/.local/bin/setup_vars_opencv4.sh
SHELL := /bin/bash

DOCKER ?= docker
TAG ?= stable
PUSH ?= true
IMAGE_NAME ?= numaflow/dci-poc-gpu-fr
IMAGE_REGISTRY = $(REGISTRY_URL)/$(IMAGE_NAME):${TAG}
DOCKER_FILE_PATH = dci_poc/vertex_gpu_fr/Dockerfile

.PHONY: update
update:
	poetry update -vv
	../../opencv-cuda/checkout-opencv-cuda.sh

.PHONY: image-push
image-push: update
	cd ../../ && $(DOCKER) buildx build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} \
	--platform linux/amd64,linux/arm64 . --push

.PHONY: image
image: update
	cd ../../ && $(DOCKER) build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} .
	@if [ "$(PUSH)" = "true" ]; then $(DOCKER) push ${IMAGE_REGISTRY}; fi

# Testing individually
test-exe:
ifndef APP
	$(error Specify tested APP. The name of APP match ../../tests/dci_poc/APP_NAME dir. ex: make test APP=APP_NAME)
endif
	PYTHONPATH=../../ poetry run pytest -s ../../tests/dci_poc/$(APP)

# Testing all at once
test-vertex:
	. ../../opencv-cuda/.local/bin/setup_vars_opencv4.sh && \
		PYTHONPATH=../../:$$PYTHONPATH FR_USE_CUDA=0 \
		poetry run pytest -s ../../tests/dci_poc/filter_resize_stream -v
	. ../../opencv-cuda/.local/bin/setup_vars_opencv4.sh && \
		PYTHONPATH=../../:$$PYTHONPATH FR_USE_CUDA=1 \
		poetry run pytest -s ../../tests/dci_poc/filter_resize_stream -v

test-setup:
	sudo apt-get update
	sudo apt-get -y install $$(grep -vE '^\s*#|^\s*$$' apt-packages.txt | sed 's/\s*#.*$$//')
	poetry install --with dev --no-root
	../../opencv-cuda/checkout-opencv-cuda.sh
	../../opencv-cuda/build-opencv-cuda.sh
