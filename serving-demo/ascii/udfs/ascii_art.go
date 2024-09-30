package udfs

import (
	"bytes"
	"context"
	"fmt"
	"image"
	"log"

	"github.com/numaproj/numaflow-go/pkg/mapper"
	"github.com/qeesung/image2ascii/convert"
)

type ImageToAscii struct {
	converter *convert.ImageConverter
}

func NewImageToAscii() *ImageToAscii {
	return &ImageToAscii{
		converter: convert.NewImageConverter(),
	}
}

func (i *ImageToAscii) Map(ctx context.Context, keys []string, d mapper.Datum) mapper.Messages {
	// build img from datum
	img, err := i.buildImageFromDatum(d)
	if err != nil {
		log.Println("Error:", err)
		return mapper.MessagesBuilder().Append(mapper.MessageToDrop())
	}

	// convert to ascii
	ascii := i.imageToAscii(img)

	// test visually :-)
	fmt.Println(ascii)

	return mapper.MessagesBuilder().Append(mapper.NewMessage([]byte(ascii)).WithKeys(keys))
}

func (i *ImageToAscii) buildImageFromDatum(d mapper.Datum) (image.Image, error) {
	reader := bytes.NewReader(d.Value())

	img, _, err := image.Decode(reader)

	return img, err
}

func (i *ImageToAscii) imageToAscii(img image.Image) string {

	// Create convert options
	convertOptions := convert.DefaultOptions

	bounds := img.Bounds()
	// TODO: fix the aspect ratio correctly
	convertOptions.FixedWidth = bounds.Dx() / 8
	convertOptions.FixedHeight = bounds.Dy() / 14

	// convert to ascii
	return i.converter.Image2ASCIIString(img, &convertOptions)
}
