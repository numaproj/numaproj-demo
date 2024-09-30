package udfs

import (
	"context"
	"image"
	"image/png"
	"log"
	"os"

	"github.com/nfnt/resize"
	"github.com/numaproj/numaflow-go/pkg/mapper"
)

type TigerImage struct {
	tiger       image.Image
	converter *ImageToAscii
}

func NewTigerImage(path string) *TigerImage {
	img, err := readImage(path)
	if err != nil {
		log.Fatalf("Failed to read image: %v", err)
	}
	return &TigerImage{
		tiger:       img,
		converter: NewImageToAscii(),
	}
}

func readImage(path string) (image.Image, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer func(file *os.File) {
		_ = file.Close()
	}(file)

	img, err := png.Decode(file)
	if err != nil {
		return nil, err
	}

	resizedImg := resize.Resize(500, 500, img, resize.Lanczos3)
	return resizedImg, nil
}

func (ct *TigerImage) Map(ctx context.Context, keys []string, datum mapper.Datum) mapper.Messages {
	asciiArt := ct.converter.imageToAscii(ct.tiger)
	log.Println(asciiArt)
	return mapper.MessagesBuilder().Append(mapper.NewMessage([]byte(asciiArt)).WithKeys(keys))
}

type DogImage struct {
	dog       image.Image
	converter *ImageToAscii
}

func NewDogImage(path string) *DogImage {
	img, err := readImage(path)
	if err != nil {
		log.Fatalf("Failed to read image: %v", err)
	}
	return &DogImage{
		dog:       img,
		converter: NewImageToAscii(),
	}
}

func (dg *DogImage) Map(ctx context.Context, keys []string, datum mapper.Datum) mapper.Messages {
	asciiArt := dg.converter.imageToAscii(dg.dog)
	log.Println(asciiArt)
	return mapper.MessagesBuilder().Append(mapper.NewMessage([]byte(asciiArt)).WithKeys(keys))
}

type ElephantImage struct {
	elephant  image.Image
	converter *ImageToAscii
}

func NewElephantImage(path string) *ElephantImage {
	img, err := readImage(path)
	if err != nil {
		log.Fatalf("Failed to read image: %v", err)
	}
	return &ElephantImage{
		elephant:  img,
		converter: NewImageToAscii(),
	}
}

func (el *ElephantImage) Map(ctx context.Context, keys []string, datum mapper.Datum) mapper.Messages {
	asciiArt := el.converter.imageToAscii(el.elephant)
	log.Println(asciiArt)
	return mapper.MessagesBuilder().Append(mapper.NewMessage([]byte(asciiArt)).WithKeys(keys))
}
