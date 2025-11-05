import os
import sys
from collections.abc import AsyncIterable
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message
from turbojpeg import TJPF_RGB, TurboJPEG

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.vertex_key_io import VertexKeyIO


class FilterResize(MapStreamer):
    def __init__(self):
        load_dotenv(str(Path(__file__).parent / '../../app.env'))

        # setup ENV
        self.fr_output_width = int(os.getenv('FR_OUTPUT_WIDTH', '416'))
        self.fr_output_height = int(os.getenv('FR_OUTPUT_HEIGHT', '416'))
        self.jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))

        # setup PyTurboJPEG
        self.jpeg = TurboJPEG()

        # setup logger
        self.logger = setup_logging('console_logger')
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'filter-resize.log')
        add_new_filehandler(self.logger, log_file)
        set_logger_log_level(self.logger)
        self.logger.info('Filter-Resize init')

    def _decompress_frame_np(
        self,
        data: bytes,
        original_height: int,
        original_width: int,
    ) -> np.ndarray:
        # switch scaling factor based on frame size in order to accelerate decode
        ratio_height = float(self.fr_output_height) / original_height
        ratio_width = float(self.fr_output_width) / original_width
        # do not scale down to smaller than output target
        ratio = max(ratio_height, ratio_width)
        # there are other scaling factors supported (such as 1/8, 3/8, or 3/4)
        # but only 1/4 and 1/2 are SIMD-accelerated
        # see: https://github.com/libjpeg-turbo/libjpeg-turbo/blob/main/README.md
        if ratio <= 0.25:
            return self.jpeg.decode(data, scaling_factor=(1, 4), pixel_format=TJPF_RGB)
        if ratio <= 0.5:
            return self.jpeg.decode(data, scaling_factor=(1, 2), pixel_format=TJPF_RGB)
        return self.jpeg.decode(data, pixel_format=TJPF_RGB)

    def _compress_frame_np(self, frame: np.ndarray) -> bytes:
        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ret:
            self.logger.error('Failed to encode frame to jpg')
            sys.exit(1)

        return buf.tobytes()

    async def handler(self, _: list[str], datum: Datum) -> AsyncIterable[Message]:
        compressed_frame = datum.value
        vk_io = VertexKeyIO(datum.keys)
        frame_idx = vk_io['frame_idx']
        original_height = vk_io['org_height']
        original_width = vk_io['org_width']

        self.logger.info(f'frame_index: {frame_idx}')
        frame = self._decompress_frame_np(compressed_frame, original_height, original_width)
        resized_frame = cv2.resize(frame, (self.fr_output_width, self.fr_output_height))
        _ = datum.event_time
        _ = datum.watermark

        if resized_frame is None or resized_frame.size == 0:
            yield Message.to_drop()
            return

        self.logger.debug(f'resized_frame: {resized_frame}')

        yield Message(
            value=self._compress_frame_np(resized_frame),
            keys=vk_io.keys_list,
        )


if __name__ == '__main__':
    handler = FilterResize()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
