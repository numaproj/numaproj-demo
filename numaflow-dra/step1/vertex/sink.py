import sys
import pickle
import signal
import subprocess

from dotenv import load_dotenv
from typing import Union

sys.path.append("../../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

from collections.abc import AsyncIterable
from pynumaflow.sinker import Datum, Responses, Response, Sinker, SinkAsyncServer

load_dotenv("../../system-config.env")

class AsyncSink(Sinker):
    def log_bbox(self, bboxes: list[tuple[float, float, float, float, float, float, int]], frame_index: int) -> None:
        for i, box in enumerate(bboxes):
            logger.info(f"frame_index: {frame_index}, box num: {i}-line1, confidence: {box[i][4]}, class_id: {box[i][6]}")
            logger.info(f"frame_index: {frame_index}, box num: {i}-line2, LeftUp: ({box[i][0]}, {box[i][1]}), RightDown: ({box[i][2]}, {box[i][3]})")

    async def handler(self, datums: AsyncIterable[Datum]) -> Responses:
        responses = Responses()
        async for msg in datums:
            bboxes = pickle.loads(msg.value)
            frame_index = msg._keys[0]
            
            self.log_bbox(bboxes, frame_index)
            
            responses.append(Response.as_success(msg.id))
        # if we are not able to write to sink and if we have a fallback sink configured
        # we can use Response.as_fallback(msg.id)) to write the message to fallback sink
        return responses


if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    set_logger_log_level(logger)
    add_new_filehandler(logger, "/var/log/numaflow/sink.log")
    
    sink_handler = AsyncSink()
    grpc_server = SinkAsyncServer(sink_handler)
    logger.info(f"grpc server start")
    grpc_server.start()
