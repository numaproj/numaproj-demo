package main

import (
	"context"
	_ "image/jpeg"
	_ "image/png"
	"log"
	"os"

	"github.com/numaproj/numaflow-go/pkg/mapper"

	"ascii-art/udfs"
)

func main() {
	allArgs := os.Args[1:]

	if len(allArgs) == 0 {
		log.Panic("Please provide the UDF type to run")
	}
	var err error
	switch allArgs[0] {
	case "planner":
		err = mapper.NewServer(&udfs.Planner{}).Start(context.Background())
	case "tiger":
		err = mapper.NewServer(udfs.NewTigerImage("/assets/tiger.png")).Start(context.Background())
	case "dog":
		err = mapper.NewServer(udfs.NewDogImage("/assets/dog.png")).Start(context.Background())
	case "elephant":
		err = mapper.NewServer(udfs.NewElephantImage("/assets/elephant.png")).Start(context.Background())
	case "asciiart":
		err = mapper.NewServer(udfs.NewImageToAscii()).Start(context.Background())
	}
	if err != nil {
		log.Panic("Failed to start map function server: ", err)
	}
}
