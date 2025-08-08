include ./../../user-config.env

TAG ?= stable
PUSH ?= true
IMAGE_REGISTRY = $(REGISTRY_URL)/numaflow/step1:${TAG}
DOCKER_FILE_PATH = step1/vertex/Dockerfile

.PHONY: update
update:
	poetry update -vv

.PHONY: image-push
image-push: update
	cd ../../ && docker buildx build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} \
	--platform linux/amd64,linux/arm64 . --push

.PHONY: image
image: update
	cd ../../ && docker build \
	-f ${DOCKER_FILE_PATH} \
	-t ${IMAGE_REGISTRY} .
	@if [ "$(PUSH)" = "true" ]; then docker push ${IMAGE_REGISTRY}; fi