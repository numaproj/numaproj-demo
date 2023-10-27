.PHONY: build
build:
	go build -v -o ./dist/traffic-analyzer main.go

.PHONY: image
image:
	docker buildx build --push -t "quay.io/numaio/numaflow-demo/traffic-analyzer:v1" --platform linux/amd64,linux/arm64 .

clean:
	-rm -rf ./dist