package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"runtime/debug"
	"strconv"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	log "github.com/sirupsen/logrus"
)

const (
	// defaultTerminationDelay delays termination of the program in a graceful shutdown situation.
	// We do this to prevent the pod from exiting immediately upon a pod termination event
	// (e.g. during a rolling update). This gives some time for ingress controllers to react to
	// the Pod IP being removed from the Service's Endpoint list, which prevents traffic from being
	// directed to terminated pods, which otherwise would cause timeout errors and/or request delays.
	// See: https://github.com/kubernetes/ingress-nginx/issues/3335#issuecomment-434970950
	defaultTerminationDelay = 1
)

var (
	fish         = os.Getenv("FISH")
	envLatency   float64
	envErrorRate int
)

var totalRequests = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "http_server_requests_seconds_count",
		Help: "Number of incoming requests",
	},
	[]string{"status", "intuit_alert"},
)

var totalRequestsLatency = prometheus.NewGaugeVec(
	prometheus.GaugeOpts{
		Name: "http_server_requests_seconds_sum",
		Help: "http request duration",
	},
	[]string{"status", "intuit_alert"},
)

func init() {
	var err error
	envLatencyStr := os.Getenv("LATENCY")
	if envLatencyStr != "" {
		envLatency, err = strconv.ParseFloat(envLatencyStr, 64)
		if err != nil {
			panic(fmt.Sprintf("failed to parse LATENCY: %s", envLatencyStr))
		}
	}
	envErrorRateStr := os.Getenv("ERROR_RATE")
	if envErrorRateStr != "" {
		envErrorRate, err = strconv.Atoi(envErrorRateStr)
		if err != nil {
			panic(fmt.Sprintf("failed to parse ERROR_RATE: %s", envErrorRateStr))
		}
	}
}

var logMessage *LogMessage

func main() {
	var (
		listenAddr       string
		terminationDelay int
		tls              bool
		configPath       string
	)
	flag.StringVar(&listenAddr, "listen-addr", ":8080", "server listen address")
	flag.IntVar(&terminationDelay, "termination-delay", defaultTerminationDelay, "termination delay in seconds")
	flag.BoolVar(&tls, "tls", false, "Enable TLS (with self-signed certificate)")
	flag.StringVar(&configPath, "logconfig", "config.yaml", "Enable TLS (with self-signed certificate)")

	flag.Parse()

	rand.Seed(time.Now().UnixNano())
	prometheus.Register(totalRequests)
	prometheus.Register(totalRequestsLatency)

	router := http.NewServeMux()
	router.Handle("/", http.StripPrefix("/", http.FileServer(http.Dir("./ui"))))

	router.HandleFunc("/fish", getFish)
	router.Handle("/metrics", promhttp.Handler())
	router.Handle("/actuator/prometheus", promhttp.Handler())
	router.Handle("/healthz", promhttp.Handler())

	metricRouter := http.NewServeMux()
	metricRouter.Handle("/metrics", promhttp.Handler())
	metricRouter.Handle("/actuator/prometheus", promhttp.Handler())
	server := &http.Server{
		Addr:    listenAddr,
		Handler: router,
	}
	metrics := &http.Server{
		Addr:    ":8490",
		Handler: metricRouter,
	}

	logMessage = NewLogMessage(configPath)

	if tls {
		tlsConfig, err := CreateServerTLSConfig("", "", []string{"localhost", "numalogic-demo", "127.0.0.1", "*"})
		if err != nil {
			log.Fatalf("Could not generate TLS config: %v\n", err)
		}
		server.TLSConfig = tlsConfig
		metrics.TLSConfig = tlsConfig
	}

	done := make(chan bool)
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-quit
		server.SetKeepAlivesEnabled(false)
		metrics.SetKeepAlivesEnabled(false)
		log.Printf("Signal %v caught. Shutting down in %vs", sig, terminationDelay)
		delay := time.NewTicker(time.Duration(terminationDelay) * time.Second)
		defer delay.Stop()
		select {
		case <-quit:
			log.Println("Second signal caught. Shutting down NOW")
		case <-delay.C:
		}

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := server.Shutdown(ctx); err != nil {
			log.Fatalf("Could not gracefully shutdown the server: %v\n", err)
		}
		close(done)
	}()
	log.Printf("Started server on %s", listenAddr)
	var err error
	if tls {
		go func() { err = metrics.ListenAndServeTLS("", "") }()
		err = server.ListenAndServeTLS("", "")
	} else {
		go func() { err = metrics.ListenAndServe() }()
		err = server.ListenAndServe()

	}
	if err != nil && err != http.ErrServerClosed {
		log.Fatalf("Could not listen on %s: %v\n", listenAddr, err)
	}

	<-done
	log.Println("Server stopped")
}

type fishParams struct {
	Fish                 string  `json:"fish"`
	DelayLength          float64 `json:"delayLength,omitempty"`
	Return500Probability *int    `json:"return500,omitempty"`
}

func getFish(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	requestBody, err := ioutil.ReadAll(r.Body)
	if err != nil {
		w.WriteHeader(500)
		log.Println(err.Error())
		fmt.Fprintf(w, err.Error())
		return
	}

	var request []fishParams
	if len(requestBody) > 0 && string(requestBody) != `"[]"` {
		err = json.Unmarshal(requestBody, &request)
		if err != nil {
			w.WriteHeader(500)
			log.Printf("%s: %v", string(requestBody), err.Error())
			fmt.Fprintf(w, err.Error())
			return
		}
	}
	//default octo fish
	if fish == "" {
		fish = "octo"
	}

	var requestParams fishParams
	for i := range request {
		cp := request[i]
		if cp.Fish == fish {
			requestParams = cp
		}
	}

	var delayLength float64
	var delayLengthStr string
	if requestParams.DelayLength > 0 {
		delayLength = requestParams.DelayLength
	} else if envLatency > 0 {
		delayLength = envLatency
	}
	if delayLength > 0 {
		delayLengthStr = fmt.Sprintf(" (%fs)", delayLength)
		time.Sleep(time.Duration(delayLength) * time.Second)
	}

	statusCode := http.StatusOK
	errorRate := envErrorRate
	if envErrorRate == 0 {
		errorRate = 1
	}

	if requestParams.Return500Probability != nil && *requestParams.Return500Probability > 0 && *requestParams.Return500Probability >= rand.Intn(100) {
		statusCode = http.StatusInternalServerError
		log.WithField("status", http.StatusInternalServerError).Errorf("msg=%s, stack=%s", logMessage.GetMessage("500"), debug.PrintStack)
		debug.PrintStack()
		totalRequests.WithLabelValues("500", "true").Inc()
	} else if envErrorRate > 0 && rand.Intn(100) < errorRate {
		statusCode = http.StatusInternalServerError
		log.WithField("status", http.StatusInternalServerError).Errorf("msg=%s, stack=%s", logMessage.GetMessage("500"), debug.PrintStack)
		//debug.PrintStack()
		totalRequests.WithLabelValues("500", "true").Inc()
	} else {
		log.WithField("status", "200").Infof("msg=%s", logMessage.GetMessage("200"))
		totalRequests.WithLabelValues("200", "true").Inc()
	}
	duration := time.Now().Sub(start).Seconds()
	totalRequestsLatency.WithLabelValues(fmt.Sprintf("%d", statusCode), "true").Set(duration)
	printFish(fish, w, statusCode)
	log.Printf("%d %f - %s%s\n", statusCode, duration, fish, delayLengthStr)
}

func printFish(fishToPrint string, w http.ResponseWriter, statusCode int) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(statusCode)
	fmt.Fprintf(w, "\"%s\"", fishToPrint)
}
