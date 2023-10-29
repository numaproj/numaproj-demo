import json
import os
from typing import Any

from langchain import PromptTemplate
from langchain.chains import LLMChain
import logging
import openai
from langchain.llms import OpenAI
from pynumaflow.mapper import Messages, Message, Datum

logger = logging.getLogger(__name__)

model_name = os.getenv("MODEL_NAME") if os.getenv("MODEL_NAME") else "text-davinci-003"
openai.api_key = os.getenv("OPENAI_API_KEY")


def remove_empty_lines(response_string: str) -> str:
    # Split the string into lines
    lines = response_string.split("\n")
    output = ""
    for line in lines:
        if len(line) == 0:
            continue
        output = output + line

    return output


class Processor:
    def initialize(self, temperature: float = 0.1):
        logger.info(model_name)
        self.llm = OpenAI(model_name=model_name, temperature=temperature)

    def __init__(self, temperature: float = 0.1):
        logger.info("Initializing Processor")
        self.llm = None
        self.initialize(temperature=temperature)

    @staticmethod
    def summary_to_jsons(
        summary: str, data: dict[str, Any], model_type: str
    ) -> dict[str, None | str | dict[str, str | Any] | dict[str, Any | None] | Any]:
        """Convert a summary to a JSON object."""
        sample_list = data.get("log_sample").split("time=")

        info = list(filter(lambda x: "level=info" in x, sample_list))
        if len(info) == 0:
            info = "N/A"
        else:
            info = "time=" + info[0]

        error = list(filter(lambda x: "level=error" in x, sample_list))
        if len(error) == 0:
            error = "N/A"
        else:
            error = "time=" + error[0]

        warn = list(filter(lambda x: "level=warn" in x, sample_list))
        if len(warn) == 0:
            warn = "N/A"
        else:
            warn = "time=" + warn[0]

        fatal = list(filter(lambda x: "level=fatal" in x, sample_list))
        if len(fatal) == 0:
            fatal = "N/A"
        else:
            fatal = "time=" + fatal[0]
        js = {
            "overall_numbers": {
                "info": data.get("info_count"),
                "error": data.get("error_count"),
                "warn": data.get("warn_count"),
                "fatal": data.get("fatal_count"),
            },
            "typical_logs": {
                "info": info,
                "error": error,
                "warn": warn,
                "fatal": fatal,
            },
            "log_clusters": data.get("log_clusters"),
            "model_type": model_type,
            "brief_summary": summary,
        }
        if data.get("event_sample") is not None:
            js["event_sample"] = data.get("event_sample")
        js["metric_scores"] = data["metric_scores"]
        return js

    def call_genai(self, data):
        prompt = PromptTemplate(
            input_variables=[
                "info_count",
                "error_count",
                "warn_count",
                "fatal_count",
                "log_sample",
                "event_sample",
            ],
            template="""
            Summarize the following log files.

            Given the following log information:
            info count:1641, error count:1109, warn count: 0, fatal count: 0
            Log type: info, log count: 1641, log sample: time="2023-09-08T20:13:36Z" level=info msg="msg=User successfully logged" status=200
            Log type: error, log count: 1109, log sample: time="2023-09-08T20:12:44Z" level=error msg="msg=panic: runtime error: invalid memory address or nil pointer dereference [signal 0xb code=0x1 addr=0x38 pc=0x26df]" status=500
            
            In addition, following kubernetes Events happened at the same time:
            9m21s       Warning   Unhealthy                pod/simple-pipeline-daemon-5b56bfb985-qzc6p    Readiness probe failed: Get "https://10.42.0.28:4327/readyz": dial tcp 10.42.0.28:4327: connect: connection refused
            5m2s        Warning   BackOff                  pod/simple-pipeline-daemon-5b56bfb985-qzc6p    Back-off restarting failed container
            
            "Summary": There are 1109 error logs indicating that there was a runtime error with an invalid memory address or nil pointer dereference.The kubernetes events events show problem with pod starting. The problem can be associated with Readiness probe failed 
            "Potential Root Cause": The readiness probe failed due to the connection refused, which may have caused the runtime error seen in the error log. The back-off restarting of the failed container may indicate an underlying issue with the pod that caused the runtime error. 
            
            Given the following log information:
            info count: {info_count}, error count: {error_count}, warn count: {warn_count}, fatal count: {fatal_count}
            {log_sample} 
            
            In addition, following kubernetes Events happened at the same time:
            {event_sample}
            
            Give me,
            "Summary":
            "Potential Root Cause":
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        out_text = chain.run(data)
        # out_text = remove_empty_lines(out_text)
        # logger.debug("\nOriginal text: ", str(data))
        # logger.debug("\nOut text: ", str(out_text))
        data["data_payload"] = self.summary_to_jsons(out_text, data, "genai")

        return data

    def udf(self, keys: list[str], datum: Datum) -> Messages:
        data_str = datum.value.decode()
        logger.info("\nReceived data_str=" + data_str)

        if len(data_str.split(" ")) > 4000:
            logger.info(
                "\nDrop message as token limit would potentially reach. data_str="
                + data_str
            )
            return Messages(Message.to_drop())

        data = json.loads(data_str)

        # Drop message if all the table catalog is empty
        # if is_catalog_empty(data):
        #    logger.info("\nDrop message as tables catalog is empty. data=", data)
        #    return Messages(Message.to_drop())

        try:
            data = self.call_genai(data)
        except Exception as err:
            logger.error("\nDrop message as there was error in calling genAI=", err)
            return Messages(Message.to_drop())

        if not json.dumps(data):
            logger.info("\nDrop message as data is empty. data=", data)
            return Messages(Message.to_drop())

        data["keys"] = keys
        response_json = json.dumps(data)
        logger.debug(f"genai:my_handler - response_json={response_json}")

        return Messages(Message(value=response_json.encode("utf-8"), keys=keys))
