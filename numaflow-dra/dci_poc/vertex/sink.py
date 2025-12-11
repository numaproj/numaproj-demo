import json
import logging
import os
import sys
from collections.abc import AsyncIterable, Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow.sinker import Datum, Response, Responses, SinkAsyncServer, Sinker

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.vertex_key_io import (
    VertexKeyIO,
)


@dataclass
class BBox:
    confidence: np.float32
    class_id: np.int64 | str
    LeftUpX: np.float32
    LeftUpY: np.float32
    RightDownX: np.float32
    RightDownY: np.float32


class FrameForVideoReceiver:
    def __init__(self, logger: logging.Logger, input_frame: np.ndarray, vk_io: VertexKeyIO):
        self.logger = logger
        self._frame_idx = vk_io['frame_idx']
        self._input: np.ndarray = input_frame
        self._output: np.ndarray | None = None
        self._bboxes: list[BBox] = []

        self.set_bboxes(vk_io)

    @property
    def output(self) -> np.ndarray | None:
        return self._output

    def set_bboxes(self, vk_io: VertexKeyIO) -> None:
        self._bboxes = [
            BBox(
                confidence=vk_io[f'box_{i}_confidence'],
                class_id=vk_io[f'box_{i}_class_id'],
                LeftUpX=vk_io[f'box_{i}_LeftUpX'],
                LeftUpY=vk_io[f'box_{i}_LeftUpY'],
                RightDownX=vk_io[f'box_{i}_RightDownX'],
                RightDownY=vk_io[f'box_{i}_RightDownY'],
            )
            for i in range(vk_io['box_len'])
        ]

    def log_input(self) -> None:
        self.logger.debug(f'input_frame: {self._input}')

    def log_bbox(self) -> None:
        for i, bbox in enumerate(self._bboxes):
            self.logger.info(
                f'frame_index: {self._frame_idx}, bbox num: {i}-line1, '
                f'confidence: {bbox.confidence}, class_id: {bbox.class_id}'
            )
            self.logger.info(
                f'frame_index: {self._frame_idx}, bbox num: {i}-line2, '
                f'LeftUp: ({bbox.LeftUpX}, {bbox.LeftUpY}), '
                f'RightDown: ({bbox.RightDownX}, {bbox.RightDownY})'
            )

    def bboxes_fusion(self):
        if self._input.ndim == 3 and self._input.shape[2] == 3:
            self._output = self._input.copy()
        else:
            msg = 'img shape must be HxW or HxWx3 (BGR).'
            raise ValueError(msg)

        # Green. BGR format(OpenCV).
        bbox_line_color = (0, 255, 0)

        # draw box
        h, w = self._input.shape[:2]
        thickness = max(1, int(min(h, w) / 200))
        for _, bbox in enumerate(self._bboxes):
            # Allow tiny epsilon because normalized outputs can slightly under/overflow [0,1].
            vals = [bbox.LeftUpX, bbox.LeftUpY, bbox.RightDownX, bbox.RightDownY]
            eps = 1e-3
            is_normalized = all(-eps <= float(v) <= 1.0 + eps for v in vals)

            if is_normalized:
                # Clip normalized values into [0,1] then scale to pixels
                lu_x = round(float(np.clip(bbox.LeftUpX, 0.0, 1.0)) * w)
                lu_y = round(float(np.clip(bbox.LeftUpY, 0.0, 1.0)) * h)
                rd_x = round(float(np.clip(bbox.RightDownX, 0.0, 1.0)) * w)
                rd_y = round(float(np.clip(bbox.RightDownY, 0.0, 1.0)) * h)
            else:
                # Treat as pixel coordinates
                lu_x = round(float(bbox.LeftUpX))
                lu_y = round(float(bbox.LeftUpY))
                rd_x = round(float(bbox.RightDownX))
                rd_y = round(float(bbox.RightDownY))

            # Final clipping to image bounds
            lu_x = max(0, min(w - 1, int(lu_x)))
            lu_y = max(0, min(h - 1, int(lu_y)))
            rd_x = max(0, min(w - 1, int(rd_x)))
            rd_y = max(0, min(h - 1, int(rd_y)))

            # Sanity check: skip invalid or degenerate boxes
            if rd_x <= lu_x or rd_y <= lu_y:
                self.logger.warning(
                    'Skipping invalid bbox (frame_index=%s): '
                    '[(%s,%s) -> (%s,%s)] from vals=%r is_normalized=%s',
                    self._frame_idx,
                    lu_x,
                    lu_y,
                    rd_x,
                    rd_y,
                    vals,
                    is_normalized,
                )
                continue

            cv2.rectangle(
                self._output,
                (lu_x, lu_y),
                (rd_x, rd_y),
                bbox_line_color,
                thickness,
            )


class AsyncSink(Sinker):
    def __init__(
        self, frame_capture_func: Callable[[int, np.ndarray, np.ndarray], None] | None = None
    ):
        load_dotenv(str(Path(__file__).parent / '../../app.env'))

        # setup logger
        self.logger = setup_logging('console_logger')
        set_logger_log_level(self.logger)
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'sink.log')
        add_new_filehandler(self.logger, log_file)
        self.frame_capture_func = frame_capture_func
        self.logger.info('Sink init')

        # setup ENV
        self.jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))
        self.receiver_url = os.getenv('RECEIVER_URL')
        if self.receiver_url is None:
            self.logger.error('environment variable RECEIVER_URL not set')
            sys.exit(1)

    def send_frame_to_video_receiver(self, frame_bgr: np.ndarray, frame_idx: int) -> None:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # buf is Raw byte data (after JPEG compression) stored in a One-dim NumPy array
        ok, buf = cv2.imencode(
            '.jpg', frame_rgb, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            self.logger.error('encode failed')
            sys.exit(1)

        files = {
            'image': ('frame.jpg', buf.tobytes(), 'image/jpeg'),
            'meta': (
                'meta.json',
                json.dumps({'frame_idx': frame_idx}, ensure_ascii=False).encode('utf-8'),
                'application/json',
            ),
        }

        r = requests.post(f'{self.receiver_url}/frame_receiver', files=files, timeout=5)
        return r

    async def handler(self, datums: AsyncIterable[Datum]) -> Responses:
        responses = Responses()
        async for msg in datums:
            resized_frame = cv2.imdecode(np.frombuffer(msg.value, np.uint8), cv2.IMREAD_UNCHANGED)
            vk_io = VertexKeyIO(msg.keys)

            self.logger.info(f'{vk_io.items()}')

            send_frame = FrameForVideoReceiver(self.logger, resized_frame, vk_io)
            send_frame.log_input()

            send_frame.bboxes_fusion()

            # Executed only during testing.
            if self.frame_capture_func is not None:
                self.frame_capture_func(vk_io['frame_idx'], resized_frame, send_frame.output)

            resp = self.send_frame_to_video_receiver(send_frame.output, vk_io['frame_idx'])

            if resp.status_code == 200:
                count = resp.json()['count']
                self.logger.debug(f'frame count: {count}')
            else:
                self.logger.error('Request failed: %s', resp.status_code)
                sys.exit(1)

            responses.append(Response.as_success(msg.id))
        # if we are not able to write to sink and if we have a fallback sink configured
        # we can use Response.as_fallback(msg.id)) to write the message to fallback sink
        return responses


if __name__ == '__main__':
    sink_handler = AsyncSink()
    grpc_server = SinkAsyncServer(sink_handler)
    grpc_server.start()
