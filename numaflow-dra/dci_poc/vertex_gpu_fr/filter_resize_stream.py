import os
import sys
from collections.abc import AsyncIterable

import cv2
import msgspec
import numpy as np
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message
from turbojpeg import TurboJPEG

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.message_spec import Payload


class FilterResize(MapStreamer):
    def __init__(self):
        # setup ENV
        self.fr_use_cuda = int(os.getenv('FR_USE_CUDA', '0')) != 0
        self.fr_output_width = int(os.getenv('FR_OUTPUT_WIDTH', '416'))
        self.fr_output_height = int(os.getenv('FR_OUTPUT_HEIGHT', '416'))
        self.jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))

        # setup CUDA memory
        self.gpumat_src = cv2.cuda_GpuMat() if self.fr_use_cuda else None

        # setup PyTurboJPEG
        self.jpeg = TurboJPEG()

        # setup logger
        self.logger = setup_logging('console_logger')
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'filter-resize.log')
        add_new_filehandler(self.logger, log_file)
        set_logger_log_level(self.logger)
        self.logger.info('Filter-Resize init')
        self.logger.info(f'cv2: {cv2.__file__}')

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
            return self.jpeg.decode(data, scaling_factor=(1, 4))
        if ratio <= 0.5:
            return self.jpeg.decode(data, scaling_factor=(1, 2))
        return self.jpeg.decode(data)

    def _compress_frame_np(self, frame: np.ndarray) -> bytes:
        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ret:
            self.logger.error('Failed to encode frame to jpg')
            sys.exit(1)

        return buf.tobytes()

    async def handler(self, _: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)
        compressed_frame = payload_in.compressed_frame
        frame_idx = payload_in.frame_index
        original_height = payload_in.original_height
        original_width = payload_in.original_width

        self.logger.info(f'frame_index: {frame_idx}')
        frame = self._decompress_frame_np(compressed_frame, original_height, original_width)

        if self.fr_use_cuda:
            self.gpumat_src.upload(frame)
            self.gpumat_dst = cv2.cuda.resize(
                self.gpumat_src, (self.fr_output_width, self.fr_output_height)
            )
            resized_frame = self.gpumat_dst.download()
        else:
            resized_frame = cv2.resize(frame, (self.fr_output_width, self.fr_output_height))

        _ = datum.event_time
        _ = datum.watermark

        if resized_frame is None or resized_frame.size == 0:
            yield Message.to_drop()
            return

        self.logger.debug(f'resized_frame: {resized_frame}')

        payload_out = Payload(
            frame_index=payload_in.frame_index,
            original_height=payload_in.original_height,
            original_width=payload_in.original_width,
            compressed_frame=self._compress_frame_np(resized_frame),
        )

        yield Message(value=msgspec.msgpack.encode(payload_out))


if __name__ == '__main__':
    handler = FilterResize()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
