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
	//go:embed generator/products.json
	products string
)

// Sample input order
//
//	{
//	  "id": "order-1730269550331762000-762",
//	  "order_time": "2024-10-29T23:25:50-07:00",
//	  "items": [
//	    {
//	      "product_id": "p-006-0005",
//	      "quantity": 2
//	    },
//	    {
//	      "product_id": "p-005-0003",
//	      "quantity": 1
//	    },
//	    {
//	      "product_id": "p-002-0007",
//	      "quantity": 2
//	    },
//	    {
//	      "product_id": "p-002-0004",
//	      "quantity": 1
//	    }
//	  ]
//	}
//
// # Sample output
//
// {"order_id":"order-1730318669701322420-175","order_time":"2024-10-30T20:04:29Z","category_id":"cate-007","category_name":"Men's Shoes","items":[{"product_id":"p-007-0001","name":"HEYDUDE Wally Stretch - Mens Comfortable Slip on Shoes","quantity":1,"price":23.99},{"product_id":"p-007-0005","name":"Vans Mountain Mule Slip On Casual Shoe Slipper Slide Quilted Black Mens Size NEW","quantity":1,"price":31.49}]}
// {"order_id":"order-1730318669701322420-175","order_time":"2024-10-30T20:04:29Z","category_id":"cate-005","category_name":"Sports Goods","items":[{"product_id":"p-005-0006","name":"6180Lbs Breaking Strength Bull Rope 1/2Inch Diameter Double Braid Polyester Rope","quantity":1,"price":30.44}]}
// {"order_id":"order-1730318669701322420-175","order_time":"2024-10-30T20:04:29Z","category_id":"cate-002","category_name":"Men's Clothing","items":[{"product_id":"p-002-0006","name":"Men's Pure Mink Cashmere Turtleneck Sweater Long-sleeved Casual Undershirts Tops","quantity":1,"price":35.99}]}
//
// Enrich and flatpmap the order info to be in different categories
func flatmap(_ context.Context, keys []string, msg mapper.Datum) mapper.Messages {
	results := mapper.MessagesBuilder()
	order := msg.Value()
	categoryMapping := make(map[string]string)
	for _, item := range gjson.GetBytes(order, "items").Array() {
		productID := item.Get("product_id").String()
		quantity := item.Get("quantity").Int()
		categoryID := getCategoryID(productID)
		categoryName := gjson.Get(products, fmt.Sprintf("%s.name", categoryID)).String()
		c, existing := categoryMapping[categoryID]
		if !existing {
			c = "{}"
			c, _ = sjson.Set(c, "order_id", gjson.GetBytes(order, "id").String())
			c, _ = sjson.Set(c, "order_time", gjson.GetBytes(order, "order_time").String())
			c, _ = sjson.Set(c, "category_id", categoryID)
			c, _ = sjson.Set(c, "category_name", categoryName)
		}
		length := len(gjson.Get(c, "items").Array())
		c, _ = sjson.Set(c, fmt.Sprintf("items.%v.product_id", length), productID)
		productName := gjson.Get(products, fmt.Sprintf(`%s.products.#(id=="%s").name`, categoryID, productID)).String()
		c, _ = sjson.Set(c, fmt.Sprintf("items.%v.name", length), productName)
		c, _ = sjson.Set(c, fmt.Sprintf("items.%v.quantity", length), quantity)
		price := gjson.Get(products, fmt.Sprintf(`%s.products.#(id=="%s").price`, categoryID, productID)).Float()
		c, _ = sjson.Set(c, fmt.Sprintf("items.%v.price", length), price)
		categoryMapping[categoryID] = c
	}
	log.Println("Enriched and flat mapped order: ")
	for categoryID, v := range categoryMapping {
		log.Println("-- ", string(v))
		results = append(results, mapper.NewMessage([]byte(v)).WithKeys([]string{categoryID}))
	}
	return results
}

func getCategoryID(productID string) string {
	result := ""
	gjson.Parse(products).ForEach(func(key, value gjson.Result) bool {
		value.Get("products").ForEach(func(_, v gjson.Result) bool {
			if v.Get("id").String() == productID {
				result = key.String()
				return true
			}
			return true
		})
		return true
	})
	return result
}

// Aggregate the order info to count the number of orders and calculate the total amount
//
// Sample output
//
//	{
//		"start": "2024-10-30T20:01:00Z",
//		"end": "2024-10-30T20:02:00Z",
//		"category_id": "cate-003",
//		"category_name": "Health & Beauty",
//		"item_count": 28,
//		"total_amount": 472.41
//	}
func aggregate(_ context.Context, keys []string, msgCh <-chan reducer.Datum, md reducer.Metadata) reducer.Messages {
	categoryID := keys[0]
	categoryName := ""
	var items = int64(0)
	var amount = float64(0)
	for msg := range msgCh {
		categoriedOrder := msg.Value()
		if categoryName == "" { // category_name will be always the same since the key for aggregation is category_id.
			categoryName = gjson.GetBytes(categoriedOrder, "category_name").String()
		}
		for _, item := range gjson.GetBytes(categoriedOrder, "items").Array() {
			price := item.Get("price").Float()
			quantity := item.Get("quantity").Int()
			amount += price * float64(quantity)
			items = items + quantity
		}
	}

	messages := reducer.MessagesBuilder()
	result := "{}"
	result, _ = sjson.Set(result, "start", md.IntervalWindow().StartTime())
	result, _ = sjson.Set(result, "end", md.IntervalWindow().EndTime())
	result, _ = sjson.Set(result, "category_id", categoryID)
	result, _ = sjson.Set(result, "category_name", categoryName)
	result, _ = sjson.Set(result, "item_count", items)
	result, _ = sjson.Set(result, "total_amount", amount)

	log.Println("Aggregated result:", result)
	return messages.Append(reducer.NewMessage([]byte(result)))
}

func main() {
	var f string
	flag.StringVar(&f, "f", "", "flag to indicate which udf to start")
	flag.Parse()

	switch f {
	case "flatmap":
		// Enrich data and flatmap
		if err := mapper.NewServer(mapper.MapperFunc(flatmap)).Start(context.Background()); err != nil {
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
