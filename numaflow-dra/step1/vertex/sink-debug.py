import sys
import pickle
import signal
import subprocess

from dotenv import load_dotenv

sys.path.append("../../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

from collections.abc import AsyncIterable
from pynumaflow.sinker import Datum, Responses, Response, Sinker, SinkAsyncServer

load_dotenv("../../system-config.env")


class AsyncSinkDebug(Sinker):
    async def handler(self, datums: AsyncIterable[Datum]) -> Responses:
        logger.debug(f"handler start")

        responses = Responses()
        async for msg in datums:
            resized_frame = pickle.loads(msg.value)
            resized_height = resized_frame.shape[0]
            resized_width  = resized_frame.shape[1]

            frame_index     = msg._keys[0]
            original_height = msg._keys[1]
            original_width  = msg._keys[2]

            logger.info(f"frame_index: {frame_index}-line1, original_height: {original_height}, original_width: {original_width}")
            logger.info(f"frame_index: {frame_index}-line2, resized_height: {resized_height}, resized_width: {resized_width}")

            responses.append(Response.as_success(msg.id))
        # if we are not able to write to sink and if we have a fallback sink configured
        # we can use Response.as_fallback(msg.id)) to write the message to fallback sink
        return responses


if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    set_logger_log_level(logger)
    add_new_filehandler(logger, "/var/log/numaflow/sink-debug.log")
    
    sink_handler = AsyncSinkDebug()
    grpc_server = SinkAsyncServer(sink_handler)
    logger.info(f"grpc server start")
    grpc_server.start()
