from pynumaflow.mapper import Messages, Message, Datum, MapServer, Mapper
from transformers import pipeline
import json
import os

os.environ['CURL_CA_BUNDLE'] = ''

class SentimentAnalyzer(Mapper):
    def __init__(self):
        self.analyzer = pipeline("sentiment-analysis")

    def handler(self, keys: list[str], datum: Datum) -> Messages:
        strs = datum.value.decode("utf-8")
        messages = Messages()
        if len(strs) == 0:
            messages.append(Message.to_drop())
            return messages

        output = {}
        sentiment = self.analyzer(strs)
        output['text'] = strs
        output['sentiment'] = sentiment[0]['label']
        output = json.dumps(output).encode("utf-8")
        messages.append(Message(output, keys=keys))
        return messages

if __name__ == "__main__":
    grpc_server = MapServer(SentimentAnalyzer())
    grpc_server.start()
