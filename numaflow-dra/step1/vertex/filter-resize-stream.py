import os
import sys
import pickle

from dotenv import load_dotenv
import cv2

from collections.abc import AsyncIterable
from pynumaflow.mapstreamer import Message, Datum, MapStreamAsyncServer, MapStreamer

load_dotenv("../../system-config.env")
OUTPUT_WIDTH = int(os.getenv("OUTPUT_WIDTH", "416"))
OUTPUT_HEIGHT = int(os.getenv("OUTPUT_HEIGHT", "416"))

sys.path.append("../../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

class FilterResize(MapStreamer):
    async def handler(self, keys: list[str], datum: Datum) -> AsyncIterable[Message]:

        frame = pickle.loads(datum.value, encoding="bytes")
        resized_frame = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (OUTPUT_WIDTH, OUTPUT_HEIGHT))
        _ = datum.event_time
        _ = datum.watermark

        logger.info(f"frame_index: {datum._keys[0]}")

        if resized_frame is None or resized_frame.size == 0:
            yield Message.to_drop()
            return

        logger.debug(f"resized_frame: {resized_frame}")

        yield Message(
            value = pickle.dumps(resized_frame),
            keys = [
                str(datum._keys[0]), # frame_index
                str(datum._keys[1]), # original_height
                str(datum._keys[2]), # original_width
            ],
        )
            

if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    add_new_filehandler(logger, "/var/log/numaflow/filter-resize.log")
    set_logger_log_level(logger)

    handler = FilterResize()
    grpc_server = MapStreamAsyncServer(handler)
    logger.info(f"grpc server start")
    grpc_server.start()
    