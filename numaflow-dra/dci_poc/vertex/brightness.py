import os
from collections.abc import AsyncIterable

import cv2
import msgspec
import numpy as np
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message

from lib.log import setup_logging
from lib.message_spec import Payload

_logger = None


def setup_logger():
    global _logger
    if _logger is None:
        _logger = setup_logging(__name__)


class BrightnessDetection(MapStreamer):
    def __init__(self):
        self._average = None
        self._brightness_threshold = float(os.getenv('BRIGHTNESS_THRESHOLD', '50.0'))
        setup_logger()
        _logger.info('Brightness detection initialized')
        _logger.info(f'BRIGHTNESS_THRESHOLD: {self._brightness_threshold}')

    async def handler(self, _keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)

        buf = np.frombuffer(payload_in.compressed_frame, np.uint8)
        bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        _, _, v = cv2.split(hsv)
        brightness = float(np.mean(v))
        tag = 'dark' if brightness < self._brightness_threshold else 'bright'

        _logger.debug(
            f'frame_index: {payload_in.frame_index}, brightness: {brightness}, tag: {tag}'
        )

        payload_out = Payload(
            frame_index=payload_in.frame_index,
            frame_width=payload_in.frame_width,
            frame_height=payload_in.frame_height,
            compressed_frame=payload_in.compressed_frame,
        )

        yield Message(
            keys=datum.keys,
            value=msgspec.msgpack.encode(payload_out),
            tags=[tag],
        )


if __name__ == '__main__':
    handler = BrightnessDetection()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
