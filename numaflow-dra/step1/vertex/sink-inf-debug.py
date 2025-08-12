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
    def log_bbox(bboxes: list[dict[str, Union[float, list[float]]]], frame_index: int) -> None:
        for i, box in enumerate(bboxes):
            logger.debug(f"frame_index: {frame_index}, box num: {i}-line1, confidence: {box['confidence']}, class_id: {box['class_id']}")
            logger.debug(f"frame_index: {frame_index}, box num: {i}-line2, x_center: {box['x_center']}, y_center: {box['y_center']}, width: {box['width']}, height: {box['height']}")

    async def handler(self, datums: AsyncIterable[Datum]) -> Responses:
        logger.debug(f"handler start")

        responses = Responses()
        async for msg in datums:
            bboxes = pickle.loads(msg.value)
            frame_index = msg._keys[0]
            #self.log_bbox(bboxes, frame_index)
            logger.info(f"frame_index: {frame_index}")

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
