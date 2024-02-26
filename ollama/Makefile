.PHONY: build
build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -o ./dist/ollama-cli main.go

.PHONY: image
image: build
	docker build -t "quay.io/numaio/numaproj-demo/ollama-cli:v0.1.0" --target ollama-cli .

clean:
	-rm -rf ./dist
