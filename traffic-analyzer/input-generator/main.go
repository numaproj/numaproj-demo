package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"strings"
	"time"

	"github.com/Shopify/sarama"
)

var (
	brokerList = os.Getenv("KAFKA_BROKERS")
	topic      = os.Getenv("KAFKA_TOPIC")
)

func main() {
	if brokerList == "" {
		log.Println("No Kafka Brokers specified, defaulting to kafka-broker:8080")
		brokerList = "numa-kafka-controller-0.numa-kafka-controller-headless.default.svc.cluster.local:9092,numa-kafka-controller-1.numa-kafka-controller-headless.default.svc.cluster.local:9092,numa-kafka-controller-2.numa-kafka-controller-headless.default.svc.cluster.local:9092"
	}

	if topic == "" {
		log.Println("No Kafka Topic specified, defaulting to input topic")
		topic = "input-topic"
	}
	log.Printf("Writing to Topic=%s Brokers=%s", topic, brokerList)

	ctx := context.Background()

	writeChan := buildKafka(ctx)

	generateMessages(ctx, writeChan)
}

func buildKafka(ctx context.Context) chan<- []byte {
	config := sarama.NewConfig()
	config.Producer.Return.Successes = true

	log.Println("Connecting to Kafka...")
	producer, err := sarama.NewSyncProducer(strings.Split(brokerList, ","), config)
	if err != nil {
		log.Fatalf("connecting to Kafka (%s) failed, %s", brokerList, err)
	}
	log.Println("Connected to Kafka")

	inputCh := make(chan []byte)

	go func() {
		for {
			select {
			case <-ctx.Done():
				log.Println("Context Done, exiting")
				return
			case msg := <-inputCh:
				pid, i, err := producer.SendMessage(&sarama.ProducerMessage{
					Topic: topic,
					Value: sarama.ByteEncoder(msg),
				})
				if err != nil {
					log.Printf("ERROR writing to Kafka (%s), %s\n", string(msg), err)
				} else {
					log.Printf("INFO wrote to partition=%d offset=%d\n", pid, i)
				}
			}
		}
	}()

	return inputCh
}

type Vehicle struct {
	VehicleID    string `json:"vehicle_id"`
	Timestamp    string `json:"timestamp"`
	Speed        int    `json:"speed"`
	VehicleType  string `json:"vehicle_type"`
	Year         int    `json:"year"`
	Color        string `json:"color"`
	LicensePlate string `json:"license_plate"`
}

var vehicleTypes = []string{"car", "truck", "motorcycle", "bus", "van"}
var colors = []string{"blue", "red", "green", "black", "white"}

func generateMessages(ctx context.Context, kafkaCh chan<- []byte) {
	for {
		message := &Vehicle{
			VehicleID:    fmt.Sprintf("VH%d", rand.Intn(10000)),
			Timestamp:    time.Now().Format(time.RFC3339),
			Speed:        rand.Intn(200),
			VehicleType:  vehicleTypes[rand.Intn(len(vehicleTypes))],
			Year:         2000 + rand.Intn(23),
			Color:        colors[rand.Intn(len(colors))],
			LicensePlate: fmt.Sprintf("ABC%d", rand.Intn(1000)),
		}

		messageBytes, err := json.Marshal(message)
		if err != nil {
			panic(err)
		}

		select {
		case <-ctx.Done():
			log.Printf("Stopping writing to Kafka, %s\n", ctx.Err())
			return
		case kafkaCh <- messageBytes:
		}

		time.Sleep(10 * time.Millisecond)
	}
}
