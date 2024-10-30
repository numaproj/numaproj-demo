VERSION ?= v0.0.1
ORDER_GEN_VERSION ?= v0.0.1

ARCHITECTURES = amd64 arm64

.PHONY: build
build:
	for arch in $(ARCHITECTURES); do \
		CGO_ENABLED=0 GOOS=linux GOARCH=$${arch} go build -v -o ./dist/emart-$${arch} main.go; \
	done

.PHONY: image
image: build
	docker build -t "quay.io/numaio/numaflow-demo/emart:${VERSION}" --target emart .

clean:
	-rm -rf ./dist

build-gen:
	for arch in $(ARCHITECTURES); do \
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./generator/dist/emart-order-gen-$${arch} ./generator/main.go; \
	done

.PHONY: image-gen
image-gen: build-gen
	docker build -t "quay.io/numaio/numaflow-demo/emart-order-gen:${ORDER_GEN_VERSION}" --target emart-order-gen -f ./generator/Dockerfile .

.PHONY: image-push
image-push: build
	docker buildx build -t quay.io/numaio/numaflow-demo/emart:${VERSION} --platform linux/amd64,linux/arm64 --target emart . --push

.PHONY: image-gen-push
image-gen-push: build-gen
	docker buildx build -t quay.io/numaio/numaflow-demo/emart-order-gen:${ORDER_GEN_VERSION} --platform linux/amd64,linux/arm64 --target emart-order-gen -f ./generator/Dockerfile . --push
