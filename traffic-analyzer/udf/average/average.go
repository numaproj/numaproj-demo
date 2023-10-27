package average

import (
	"context"
	"encoding/json"
	"log"

	"github.com/numaproj/numaflow-go/pkg/reducer"
	"go.uber.org/zap"

	"traffic-analyzer/observability"
)

var AVERAGE_UDF = "COMPUTE_AVERAGE_UDF"

// ReduceHandle to calculate average speed of vehicles in a given time window
// output will be a json with following fields - avg_speed, vehicles_count, timestamp
func ReduceHandle(_ context.Context, keys []string, reduceCh <-chan reducer.Datum, metadata reducer.Metadata) reducer.Messages {

	avgSpeed := 0.0
	count := 0

	for d := range reduceCh {
		var inputObj map[string]interface{}
		err := json.Unmarshal(d.Value(), &inputObj)
		if err != nil {
			log.Println("Error while deserializing input json - ", err.Error())
			continue
		}

		speed, ok := inputObj["speed"]

		if !ok {
			continue
		}

		avgSpeed += speed.(float64)
		count++

	}

	if count != 0 {
		avgSpeed = avgSpeed / float64(count)
	}

	outputBytes, err := json.Marshal(map[string]interface{}{
		"vehicles_count": count,
		"avg_speed":      avgSpeed,
		"timestamp":      metadata.IntervalWindow().StartTime().UnixMilli(),
	})

	if err != nil {
		observability.Logger.Error("Error while serializing output data - ", zap.Error(err))
		return reducer.MessagesBuilder().Append(reducer.MessageToDrop())
	}

	return reducer.MessagesBuilder().Append(reducer.NewMessage(outputBytes).WithKeys(keys))
}
