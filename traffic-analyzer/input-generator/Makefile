.PHONY: build
build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./dist/generator main.go

.PHONY: image
image: build
	docker build -t "quay.io/numaio/numaflow-demo/generator:v1" --target generator .

clean:
	-rm -rf ./dist
