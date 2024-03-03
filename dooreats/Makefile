.PHONY: build
build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./dist/dooreats main.go

.PHONY: image
image: build
	docker build -t "quay.io/numaio/numaflow-demo/dooreats:v0.0.1" --target dooreats .

clean:
	-rm -rf ./dist

build-gen:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./generator/dist/order-gen ./generator/main.go

.PHONY: image-gen
image-gen: build-gen
	docker build -t "quay.io/numaio/numaflow-demo/dooreats-order-gen:v0.0.1" --target order-gen -f ./generator/Dockerfile .
