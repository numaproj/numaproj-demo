package main

import (
	"context"
	_ "embed"
	"flag"
	"fmt"
	"log"

	"github.com/numaproj/numaflow-go/pkg/mapper"
	"github.com/numaproj/numaflow-go/pkg/reducer"
	"github.com/tidwall/gjson"
	"github.com/tidwall/sjson"
)

var (
	//go:embed generator/restaurants.json
	restaurants string
)

// Sample input order
//
//	{
//	  "id": "order-1709279048525074000-594",
//	  "restaurant_id": "rstt-003",
//	  "order_time": "2024-02-29T23:44:08-08:00",
//	  "dishes": [
//	    {
//	      "dish_id": "rstt-003-d003",
//	      "quantity": 1
//	    },
//	    {
//	      "dish_id": "rstt-003-d002",
//	      "quantity": 1
//	    }
//	  ]
//	}
//
// # Sample output
//
//	{
//	  "id": "order-1709279048525074000-594",
//	  "restaurant_id": "rstt-003",
//	  "restaurant_name": "Paesano Ristorante Italiano",        -- added
//	  "order_time": "2024-02-29T23:44:08-08:00",
//	  "dishes": [
//	    {
//	      "dish_id": "rstt-003-d003",
//	      "price": 15.95,                                      -- added
//	      "quantity": 1
//	    },
//	    {
//	      "dish_id": "rstt-003-d002",
//	      "price": 21.95,                                      -- added
//	      "quantity": 1
//	    }
//	  ]
//	}
//
// Enrich the order info to add restaurant name and price for each dish
func enrich(_ context.Context, keys []string, msg mapper.Datum) mapper.Messages {
	results := mapper.MessagesBuilder()
	order := msg.Value()
	restaurantID := gjson.GetBytes(order, "restaurant_id").String()
	restaurantName := gjson.Get(restaurants, fmt.Sprintf("%s.name", restaurantID)).String()
	enrichedOrder, _ := sjson.SetBytes(order, "restaurant_name", restaurantName)
	for i, dish := range gjson.GetBytes(order, "dishes").Array() {
		dishID := dish.Get("dish_id").String()
		price := gjson.Get(restaurants, fmt.Sprintf(`%s.menu.#(id=="%s").price`, restaurantID, dishID)).Float()
		enrichedOrder, _ = sjson.SetBytes(enrichedOrder, fmt.Sprintf("dishes.%v.price", i), price)
	}

	log.Println("Enriched order: ", string(enrichedOrder))
	results = append(results, mapper.NewMessage(enrichedOrder).WithKeys([]string{restaurantName}))
	return results
}

// Aggregate the order info to count the number of orders and calculate the total amount
func aggregate(_ context.Context, keys []string, msgCh <-chan reducer.Datum, md reducer.Metadata) reducer.Messages {
	restaurantName := keys[0]
	var orderCounter = 0
	var amount = float64(0)
	for msg := range msgCh {
		orderCounter++
		order := msg.Value()
		for _, dish := range gjson.GetBytes(order, "dishes").Array() {
			price := dish.Get("price").Float()
			quantity := dish.Get("quantity").Int()
			amount += price * float64(quantity)
		}
	}

	messages := reducer.MessagesBuilder()
	result := "{}"
	result, _ = sjson.Set(result, "start", md.IntervalWindow().StartTime())
	result, _ = sjson.Set(result, "end", md.IntervalWindow().EndTime())
	result, _ = sjson.Set(result, "restaurant_name", restaurantName)
	result, _ = sjson.Set(result, "order_count", orderCounter)
	result, _ = sjson.Set(result, "total_amount", amount)

	log.Println("Aggregated result:", result)
	return messages.Append(reducer.NewMessage([]byte(result)))
}

func main() {
	var f string
	flag.StringVar(&f, "f", "", "flag to indicate which udf to start")
	flag.Parse()

	switch f {
	case "enrich":
		// Enrich data
		if err := mapper.NewServer(mapper.MapperFunc(enrich)).Start(context.Background()); err != nil {
			log.Panic("Failed to start enrichment function server: ", err)
		}
	case "aggr":
		// Aggregate data
		err := reducer.NewServer(reducer.SimpleCreatorWithReduceFn(aggregate)).Start(context.Background())
		if err != nil {
			log.Panic("Failed to start aggregation function server: ", err)
		}
	default:
		log.Panic("Not implemented.")
	}
}
