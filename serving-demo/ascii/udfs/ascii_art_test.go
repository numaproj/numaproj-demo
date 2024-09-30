package udfs

import (
	"bytes"
	"context"
	"image"
	"image/png"
	"log"
	"os"
	"testing"
	"time"
)

type TestDatum struct {
	value   []byte
	headers map[string]string
}

func (t *TestDatum) Value() []byte {
	return t.value
}

func (t *TestDatum) EventTime() time.Time {
	return time.Now()
}

func (t *TestDatum) Watermark() time.Time {
	return time.Now()
}

func (t *TestDatum) Headers() map[string]string {
	return t.headers
}

func TestImageToAsciiFromBytes(t *testing.T) {
	var images = []string{"assets/luffy.jpg", "assets/numa-128.png", "assets/intuit-logo.png", "assets/numa-512.png"}
	for _, img := range images {
		img, err := loadImage(img)
		if err != nil {
			log.Fatalf("failed to load image: %v", err)
		}

		buf := new(bytes.Buffer)

		err = png.Encode(buf, img)
		if err != nil {
			log.Fatalf("failed to encode image: %v", err)
		}

		imgBytes := buf.Bytes()
		datum := &TestDatum{value: imgBytes}
		converter := NewImageToAscii()
		converter.Map(context.Background(), []string{}, datum)
	}
}

func loadImage(path string) (image.Image, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	img, _, err := image.Decode(bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	return img, nil
}
