import os
import sys
import pickle

from dotenv import load_dotenv
import cv2

from pynumaflow.mapper import Messages, Message, Datum, MapAsyncServer, Mapper

load_dotenv("../../system-config.env")
OUTPUT_WIDTH = int(os.getenv("OUTPUT_WIDTH", "416"))
OUTPUT_HEIGHT = int(os.getenv("OUTPUT_HEIGHT", "416"))

sys.path.append("../../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

class FilterResize(Mapper):
    async def handler(self, keys: list[str], datum: Datum) -> Messages:
        logger.debug(f"handler start")

        frame = pickle.loads(datum.value, encoding="bytes")
        logger.debug(f"recieve data")
        resized_frame = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (OUTPUT_WIDTH, OUTPUT_HEIGHT))
        logger.debug(f"resized frame")
        _ = datum.event_time
        _ = datum.watermark

        messages = Messages()
        if frame is None:
            messages.append(Message.to_drop())
            return meesages

        logger.debug(f"output message")        
        messages.append(
            Message(
                value = pickle.dumps(resized_frame),
                keys = [
                    str(datum._keys[0]), # frame_index
                    str(datum._keys[1]), # original_height
                    str(datum._keys[2]), # original_width
                ],
            )
        )
        return messages


if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    add_new_filehandler(logger, "/var/log/numaflow/filter-resize.log")
    set_logger_log_level(logger)

    handler = FilterResize()
    grpc_server = MapAsyncServer(handler)
    logger.info(f"grpc server start")
    grpc_server.start()

    logger.info(f"grpc server end")
    