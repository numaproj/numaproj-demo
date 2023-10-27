package keying

import (
	"context"
	"encoding/json"

	"github.com/numaproj/numaflow-go/pkg/mapper"
	"go.uber.org/zap"

	"traffic-analyzer/observability"
)

var KEYING_UDF = "KEYING_UDF"

// MapHandle to create a new message with keys and tags, keys will be vehicle_type and color, tag will be vehicle_type
func MapHandle(_ context.Context, keys []string, d mapper.Datum) mapper.Messages {
	msg := d.Value()
	_ = d.EventTime() // Event time is available
	_ = d.Watermark() // Watermark is available

	var jsonObject map[string]interface{}
	err := json.Unmarshal(msg, &jsonObject)
	if err != nil {
		observability.Logger.Error("Error while deserializing input json dropping the message - ", zap.Error(err))
		return mapper.MessagesBuilder().Append(mapper.MessageToDrop())
	}

	vehicleType, vtIsPresent := jsonObject["vehicle_type"]
	color, cIsPresent := jsonObject["color"]
	if !vtIsPresent || !cIsPresent || len(vehicleType.(string)) == 0 || len(color.(string)) == 0 {
		// if vehicleType or color is not present in the input json, drop the message
		observability.Logger.Warn("dropping the invalid message - ", zap.Binary("value", d.Value()))
		return mapper.MessagesBuilder().Append(mapper.MessageToDrop())
	}

	var tags []string

	if vehicleType.(string) == "car" {
		tags = []string{"car"}
	} else {
		tags = []string{"not_car"}
	}

	// Create a new message with keys and tags, keys will be vehicle_type and color, tag will be vehicle_type
	messages := mapper.MessagesBuilder().Append(mapper.NewMessage(msg).WithKeys([]string{vehicleType.(string), color.(string)}).WithTags(tags))

	return messages
}
