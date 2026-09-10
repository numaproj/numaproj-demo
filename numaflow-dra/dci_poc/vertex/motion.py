import os
from collections.abc import AsyncIterable

import cv2
import msgspec
import numpy as np
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message

from lib.log import setup_logging
from lib.message_spec import BoundingBox, Payload

_logger = None


def setup_logger():
    global _logger
    if _logger is None:
        _logger = setup_logging(__name__)


class MotionDetection(MapStreamer):
    def __init__(self):
        self._average = None
        self._accumulate_weight = float(os.getenv('MOTION_ACCUMULATE_WEIGHT', '0.5'))
        self._binary_threshold = int(os.getenv('MOTION_BINARY_THRESHOLD', '5'))
        self._contour_threshold = int(os.getenv('MOTION_CONTOUR_THRESHOLD', '500'))
        setup_logger()
        _logger.info('Motion detection initialized')
        _logger.info(f'MOTION_ACCUMULATE_WEIGHT: {self._accumulate_weight}')
        _logger.info(f'MOTION_BINARY_THRESHOLD: {self._binary_threshold}')
        _logger.info(f'MOTION_CONTOUR_THRESHOLD: {self._contour_threshold}')

    async def handler(self, _keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)

        buf = np.frombuffer(payload_in.compressed_frame, np.uint8)
        bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        if self._average is None:
            self._average = gray.copy().astype('float')

        delta = cv2.absdiff(gray, cv2.convertScaleAbs(self._average))
        # Update average after computing diff in order to support weight=1
        self._average = cv2.accumulateWeighted(gray, self._average, self._accumulate_weight)

        _, thresh = cv2.threshold(delta, self._binary_threshold, 255, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        contours = list(filter(lambda c: cv2.contourArea(c) >= self._contour_threshold, contours))

        rectangles = [cv2.boundingRect(c) for c in contours]
        _logger.debug(f'rectangles: {rectangles}')

        bboxes = [
            BoundingBox(
                class_id=0,
                confidence=1.0,
                top_left_x=r[0],
                top_left_y=r[1],
                bottom_right_x=(r[0] + r[2]),
                bottom_right_y=(r[1] + r[3]),
            )
            for r in rectangles
        ]

        payload_out = Payload(
            frame_index=payload_in.frame_index,
            bounding_boxes=bboxes,
            compressed_frame=payload_in.compressed_frame,
        )

        yield Message(
            keys=datum.keys,
            value=msgspec.msgpack.encode(payload_out),
        )


if __name__ == '__main__':
    handler = MotionDetection()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
