include ./../../repo.env

DOCKER ?= docker
TAG ?= stable
PUSH ?= true
IMAGE_NAME ?= numaflow/dci-poc
IMAGE_REGISTRY = $(REGISTRY_URL)/$(IMAGE_NAME):${TAG}
DOCKER_FILE_PATH = dci_poc/vertex/Dockerfile

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
test-ut:
	PYTHONPATH=../../ SOURCE_INPUT_TYPE=file poetry run pytest -s ../../tests/dci_poc/source/test_source.py::test_source_under_file_src -v
	PYTHONPATH=../../ SOURCE_INPUT_TYPE=stream poetry run pytest -s ../../tests/dci_poc/source/test_source.py::test_source_under_stream_src -v
	PYTHONPATH=../../ poetry run pytest -s ../../tests/dci_poc/filter_resize_stream -v
	PYTHONPATH=../../ poetry run pytest -s ../../tests/dci_poc/sink -v

test-setup:
	sudo apt-get update
	sudo apt-get -y install $$(grep -vE '^\s*#|^\s*$$' apt-packages.txt | sed 's/\s*#.*$$//')
	poetry install --with dev --no-root
