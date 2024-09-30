package udfs

import (
	"context"
	"encoding/json"
	"testing"
)

func TestForwardMap(t *testing.T) {
	animals := []string{"tiger", "dog", "elephant"}
	jsonValue, _ := json.Marshal(map[string]interface{}{
		"animals": animals,
	})

	datum := &TestDatum{
		value: jsonValue,
		headers: map[string]string{
			"content-type": "application/json",
		},
	}

	forward := &Planner{}
	messages := forward.Map(context.Background(), []string{}, datum)
	tags := messages.Items()[0].Tags()
	if len(tags) != len(animals) {
		t.Errorf("Expected %d tags, got %d", len(animals), len(tags))
	}

	for i, tag := range tags {
		if tag != animals[i] {
			t.Errorf("Expected tag %s, got %s", animals[i], tag)
		}
	}
}

func TestForwardMapError(t *testing.T) {
	animals := []string{"tiger", "dog", "elephant"}
	jsonValue, _ := json.Marshal(map[string]interface{}{
		"animals": animals,
	})

	datum := &TestDatum{
		value: jsonValue,
		headers: map[string]string{
			"content-type": "unsupported/content-type",
		},
	}

	forward := &Planner{}
	messages := forward.Map(context.Background(), []string{}, datum)

	if len(messages.Items()) != 1 {
		t.Errorf("Expected 1 message, got %d", len(messages.Items()))
	}

	var errorMsg map[string]string
	err := json.Unmarshal(messages.Items()[0].Value(), &errorMsg)
	if err != nil {
		t.Errorf("Failed to parse error message: %v", err)
	}

	if errorMsg["error"] != "Unsupported content type" {
		t.Errorf("Expected error message 'Unsupported content type', got '%s'", errorMsg["error"])
	}
}
