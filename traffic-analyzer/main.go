package main

import (
	"context"
	"os"

	"github.com/numaproj/numaflow-go/pkg/mapper"
	"github.com/numaproj/numaflow-go/pkg/reducer"
	"go.uber.org/zap"

	"traffic-analyzer/observability"
	"traffic-analyzer/udf/average"
	"traffic-analyzer/udf/keying"
)

func main() {
	var (
		udfName = os.Getenv("UDF_NAME")
		err     error
		ctx     = context.Background()
	)

	allArgs := os.Args[1:]
	observability.Logger.Info("Arguments provided - ", zap.Strings("args", allArgs))

	// based on the udf name, start the appropriate grpc server
	if udfName == keying.KEYING_UDF {
		observability.Logger.Info("Starting keying udf server")
		err = mapper.NewServer(mapper.MapperFunc(keying.MapHandle)).Start(ctx)
	} else if udfName == average.AVERAGE_UDF {
		observability.Logger.Info("Starting reduce udf server")
		err = reducer.NewServer(reducer.ReducerFunc(average.ReduceHandle)).Start(ctx)
	} else {
		observability.Logger.Panic("Invalid udf name")
	}
	if err != nil {
		observability.Logger.Panic("Error while starting grpc server", zap.Error(err))
	}

}
