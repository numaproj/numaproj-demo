VERSION ?= v0.0.2
ORDER_GEN_VERSION ?= v0.0.2

ARCHITECTURES = amd64 arm64

.PHONY: build
build:
	for arch in $(ARCHITECTURES); do \
		CGO_ENABLED=0 GOOS=linux GOARCH=$${arch} go build -v -o ./dist/dooreats-$${arch} main.go; \
	done

.PHONY: image
image: build
	docker build -t "quay.io/numaio/numaflow-demo/dooreats:${VERSION}" --target dooreats .

clean:
	-rm -rf ./dist

build-gen:
	for arch in $(ARCHITECTURES); do \
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./generator/dist/order-gen-$${arch} ./generator/main.go; \
	done

.PHONY: image-gen
image-gen: build-gen
	docker build -t "quay.io/numaio/numaflow-demo/dooreats-order-gen:${ORDER_GEN_VERSION}" --target order-gen -f ./generator/Dockerfile .

.PHONY: image-push
image-push: build
	docker buildx build -t quay.io/numaio/numaflow-demo/dooreats:${VERSION} --platform linux/amd64,linux/arm64 --target dooreats . --push

.PHONY: image-gen-push
image-gen-push: build-gen
	docker buildx build -t quay.io/numaio/numaflow-demo/dooreats-order-gen:${ORDER_GEN_VERSION} --platform linux/amd64,linux/arm64 --target order-gen -f ./generator/Dockerfile . --push
