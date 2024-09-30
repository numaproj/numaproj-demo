package udfs

import (
	"context"
	"encoding/json"
	"log"

	"github.com/numaproj/numaflow-go/pkg/mapper"
)

type Planner struct{}

func (f *Planner) Map(ctx context.Context, keys []string, datum mapper.Datum) mapper.Messages {
	headers := datum.Headers()
	contentType, ok := headers["content-type"]
	if !ok {
		log.Println("content-type header is missing")
		return mapper.MessagesBuilder().Append(mapper.NewMessage(constructErrorJSON("Content-Type header is missing")).WithTags([]string{"error"}))
	}

	switch contentType {
	case "image/png":
		return f.handleImage(keys, datum)
	case "application/json":
		return f.handleJSON(keys, datum)
	default:
		log.Println("Unsupported content type: ", contentType)
		return mapper.MessagesBuilder().Append(mapper.NewMessage(constructErrorJSON("Unsupported content type")).WithTags([]string{"error"}))
	}
}

func (f *Planner) handleImage(keys []string, datum mapper.Datum) mapper.Messages {
	return mapper.MessagesBuilder().Append(mapper.NewMessage(datum.Value()).WithTags([]string{"asciiart"}).WithKeys(keys))
}

func (f *Planner) handleJSON(keys []string, datum mapper.Datum) mapper.Messages {
	var jsonObj map[string]interface{}
	err := json.Unmarshal(datum.Value(), &jsonObj)
	if err != nil {
		log.Println("Failed to parse JSON: ", err.Error())
		return mapper.MessagesBuilder().Append(mapper.NewMessage(constructErrorJSON("Failed to parse JSON")).WithTags([]string{"error"}))
	}

	animals, ok := jsonObj["animals"].([]interface{})
	if !ok {
		log.Println("Failed to parse animals")
		return mapper.MessagesBuilder().Append(mapper.MessageToDrop())
	}

	allowedAnimals := map[string]bool{"tiger": true, "dog": true, "elephant": true}
	var tags []string

	for _, animal := range animals {
		animalStr, ok := animal.(string)
		if !ok || !allowedAnimals[animalStr] {
			log.Println("Unsupported animal: ", animalStr)
			return mapper.MessagesBuilder().Append(mapper.NewMessage(constructErrorJSON("Unsupported animal")).WithTags([]string{"error"}))
		}
		log.Println("Animal: ", animalStr)
		tags = append(tags, animalStr)
	}

	return mapper.MessagesBuilder().Append(mapper.NewMessage(datum.Value()).WithTags(tags).WithKeys(keys))
}

func constructErrorJSON(errorMessage string) []byte {
	errorJSON := map[string]string{
		"error": errorMessage,
	}
	errorJSONBytes, _ := json.Marshal(errorJSON)
	return errorJSONBytes
}
