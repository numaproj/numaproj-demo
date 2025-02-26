package main

import (
	_ "embed"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"os"
	"os/signal"
	"slices"
	"strconv"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	"github.com/tidwall/gjson"
	"github.com/tidwall/sjson"
)

var (
	//go:embed products.json
	products string
)

func generateOrderID() string {
	return "order-" + fmt.Sprint(time.Now().UnixNano()) + "-" + strconv.Itoa(rand.Intn(1000))
}

func randomProductIDs() []string {
	produceIDs := []string{}
	gjson.Parse(products).ForEach(func(key, value gjson.Result) bool {
		value.Get("products").ForEach(func(key, v gjson.Result) bool {
			produceIDs = append(produceIDs, v.Get("id").String())
			return true
		})
		return true
	})

	results := []string{}
	r := len(produceIDs)
	if r > 10 { // max 10
		r = 10
	}
	for i := 0; i <= rand.Intn(r); i++ {
		id := produceIDs[rand.Intn(len(produceIDs))]
		if !slices.Contains(results, id) {
			results = append(results, id)
		}
	}
	return results
}

// Ramdomly generate an order information
func generateOrder() string {
	s := "{}"
	s, _ = sjson.Set(s, "id", generateOrderID())
	s, _ = sjson.Set(s, "order_time", time.Now().Format(time.RFC3339))
	for i, productID := range randomProductIDs() {
		s, _ = sjson.Set(s, fmt.Sprintf("items.%v.product_id", i), productID)
		s, _ = sjson.Set(s, fmt.Sprintf("items.%v.quantity", i), rand.Intn(2)+1) // random 1 or 2
	}
	return s
}

func createTopicIfNotExist(brokers []string, topic string) error {
	admin, err := sarama.NewClusterAdmin(brokers, sarama.NewConfig())
	if err != nil {
		return fmt.Errorf("failed to get a new sarama admin client, %w", err)
	}
	defer admin.Close()
	topics, err := admin.ListTopics()
	if err != nil {
		return fmt.Errorf("failed to list kafka topics, %w", err)
	}
	if _, ok := topics[topic]; ok {
		return nil
	}
	if err = admin.CreateTopic(topic, &sarama.TopicDetail{NumPartitions: 1, ReplicationFactor: 1}, true); err != nil {
		return fmt.Errorf("failed to create a kafka topic, %w", err)
	}
	return nil
}

func main() {
	var broker string
	var topic string
	flag.StringVar(&broker, "broker", "", "Kafka broker")
	flag.StringVar(&topic, "topic", "", "Kafka topic")
	flag.Parse()

	if broker == "" || topic == "" {
		log.Panic("Kafka broker and topic are required")
	}

	if err := createTopicIfNotExist([]string{broker}, topic); err != nil {
		log.Panic(err)
	}

	// Create the output topic as well
	if err := createTopicIfNotExist([]string{broker}, topic+"-output"); err != nil {
		log.Panic(err)
	}

	config := sarama.NewConfig()
	config.Producer.Return.Successes = true

	syncProducer, err := sarama.NewSyncProducer([]string{broker}, config)
	if err != nil {
		log.Panic(err)
	}
	defer syncProducer.Close()

	signalCh := make(chan os.Signal, 1)
	signal.Notify(signalCh, os.Interrupt, syscall.SIGTERM)

	for {
		select {
		case <-signalCh:
			log.Println("Shutting down...")
			return
		default:
		}
		time.Sleep(time.Duration(rand.Intn(3000)) * time.Millisecond)
		orderInfo := generateOrder()
		log.Println("Order: ", orderInfo)
		message := &sarama.ProducerMessage{
			Topic: topic,
			Value: sarama.ByteEncoder([]byte(orderInfo)),
		}

		if _, _, err := syncProducer.SendMessage(message); err != nil {
			log.Println("Failed to send a message: ", err)
		}
	}
}
