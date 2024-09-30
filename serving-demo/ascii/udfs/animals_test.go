package udfs

import (
	"context"
	"testing"
)

func TestTigerImageMap(t *testing.T) {
	tigerImage := NewTigerImage("assets/tiger.png")
	datum := &TestDatum{value: []byte("test")}
	messages := tigerImage.Map(context.Background(), []string{}, datum)

	if len(messages.Items()) == 0 {
		t.Errorf("Expected at least one message, got none")
	}
}

func TestDogImageMap(t *testing.T) {
	dogImage := NewDogImage("assets/dog.png")
	datum := &TestDatum{value: []byte("test")}
	messages := dogImage.Map(context.Background(), []string{}, datum)

	if len(messages.Items()) == 0 {
		t.Errorf("Expected at least one message, got none")
	}
}

func TestElephantImageMap(t *testing.T) {
	elephantImage := NewElephantImage("assets/elephant.png")
	datum := &TestDatum{value: []byte("test")}
	messages := elephantImage.Map(context.Background(), []string{}, datum)

	if len(messages.Items()) == 0 {
		t.Errorf("Expected at least one message, got none")
	}
}
