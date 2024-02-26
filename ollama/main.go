package main

import (
	"context"
	"crypto/tls"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/numaproj/numaflow-go/pkg/mapper"
)

var (
	httpClient = &http.Client{
		Timeout: 180 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}
)

func handle(_ context.Context, keys []string, d mapper.Datum) mapper.Messages {
	results := mapper.MessagesBuilder()
	msg := d.Value()
	resp, err := httpClient.Post("http://localhost:11434/api/generate", "application/json", strings.NewReader(string(msg)))
	if err != nil {
		log.Println("Failed to call ollama: ", err)
		results = results.Append(mapper.MessageToDrop())
		return results
	}
	defer resp.Body.Close()
	m, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Println("Failed to read response: ", err)
		results = results.Append(mapper.MessageToDrop())
		return results
	}
	results = results.Append(mapper.NewMessage(m))
	return results
}

func main() {
	if err := mapper.NewServer(mapper.MapperFunc(handle)).Start(context.Background()); err != nil {
		log.Panic("Failed to start: ", err)
	}
}
