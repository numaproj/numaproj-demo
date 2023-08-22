package main

import (
	log "github.com/sirupsen/logrus"
	"gopkg.in/yaml.v2"
	"math/rand"
	"os"
)

type LogMessage struct {
	Message map[string][]string
}

func NewLogMessage(path string) *LogMessage {
	logMsg := LogMessage{}
	f, err := os.ReadFile(path)
	if err != nil {
		log.Fatal(err)
	}
	logMsg.Message = make(map[string][]string)
	yaml.Unmarshal(f, logMsg.Message)
	log.Println(logMsg)
	return &logMsg
}

func (lm *LogMessage) GetMessage(code string) string {
	msgs := lm.Message[code]
	indx := rand.Intn(len(msgs))
	return msgs[indx]
}
