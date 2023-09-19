package main

import (
	log "github.com/sirupsen/logrus"
	"gopkg.in/yaml.v2"
	"math/rand"
	"os"
)

type LogMessage struct {
	logEnable bool
	Message   map[string][]string
}

func NewLogMessage(path string, enable bool) *LogMessage {
	logMsg := LogMessage{}
	logMsg.logEnable = enable
	logMsg.Message = make(map[string][]string)
	if enable {
		f, err := os.ReadFile(path)
		if err != nil {
			log.Fatal(err)
		}
		yaml.Unmarshal(f, logMsg.Message)
		log.Println(logMsg)
	}
	return &logMsg
}
func (lm *LogMessage) IsEnable() bool {
	return lm.logEnable
}

func (lm *LogMessage) GetMessage(code string) string {
	if lm.logEnable {
		msgs := lm.Message[code]
		indx := rand.Intn(len(msgs))
		return msgs[indx]
	} else {
		return ""
	}

}
