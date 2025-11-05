include ./../../repo.env

DOCKER ?= docker
TAG ?= stable
PUSH ?= true
IMAGE_NAME ?= numaflow/dci-poc-gpu-yolov4
IMAGE_REGISTRY = $(REGISTRY_URL)/$(IMAGE_NAME):${TAG}
DOCKER_FILE_PATH = dci_poc/vertex_gpu_yolov4/Dockerfile

.PHONY: update
update:
	poetry update -vv

.PHONY: image-push
image-push: update
	cd ../../ && $(DOCKER) buildx build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} \
	--platform linux/amd64,linux/arm64 . --push

.PHONY: image
image: update
	cd ../../ && \
	export $(grep -vE '^\s*#|^\s*$' repo.env | sed 's/\s*#.*$//') && \
	$(DOCKER) build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} \
	--build-arg YOLOV4_GIT_VERSION=${YOLOV4_GIT_VERSION} \
	--build-arg YOLOV4_GIT_URL=${YOLOV4_GIT_URL} \
	--build-arg YOLOV4_DL_MODEL_WEIGHTS_URL=${YOLOV4_DL_MODEL_WEIGHTS_URL} \
	--build-arg YOLOV4_DL_MODEL_URL=${YOLOV4_DL_MODEL_URL} \
	.
	@if [ "$(PUSH)" = "true" ]; then $(DOCKER) push ${IMAGE_REGISTRY}; fi

# Testing individually
test-exe:
ifndef APP
	$(error Specify tested APP. The name of APP match ../../tests/dci_poc/APP_NAME dir. ex: make test APP=APP_NAME)
endif
	PYTHONPATH=../../ poetry run pytest -s ../../tests/dci_poc/$(APP)

# Testing all at once (but no unit test yet)
test-ut:
	PYTHONPATH=../../ poetry run pytest -s ../../tests/dci_poc/inference_stream -v

test-setup:
	sudo apt-get update
	sudo apt-get -y install $$(grep -vE '^\s*#|^\s*$$' apt-packages.txt | sed 's/\s*#.*$$//')
	poetry install --with dev --no-root
