import os
import sys
from collections.abc import AsyncIterable

import cv2
import msgspec
import numpy as np
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message
from turbojpeg import TurboJPEG

from lib.log import setup_logging
from lib.message_spec import Payload

_logger = None


def setup_logger():
    global _logger
    if _logger is None:
        _logger = setup_logging(__name__)


class FilterResize(MapStreamer):
    def __init__(self):
        # setup ENV
        self.fr_use_cuda = int(os.getenv('FR_USE_CUDA', '0')) != 0
        self.fr_output_width = int(os.getenv('FR_OUTPUT_WIDTH', '416'))
        self.fr_output_height = int(os.getenv('FR_OUTPUT_HEIGHT', '416'))
        self.keep_secondary_frame = int(os.getenv('KEEP_SECONDARY_FRAME', '0')) != 0
        self.jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))

        # setup CUDA memory
        self.gpumat_src = cv2.cuda_GpuMat() if self.fr_use_cuda else None

        # setup PyTurboJPEG
        self.jpeg = TurboJPEG()

        setup_logger()
        _logger.info('Filter resize initialized')
        _logger.info(f'cv2: {cv2.__file__}')

    def _decompress_frame_np(
        self,
        data: bytes,
        frame_height: int,
        frame_width: int,
    ) -> np.ndarray:
        # switch scaling factor based on frame size in order to accelerate decode
        ratio_height = float(self.fr_output_height) / frame_height
        ratio_width = float(self.fr_output_width) / frame_width
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
            _logger.error('Failed to encode frame to jpg')
            sys.exit(1)

        return buf.tobytes()

    async def handler(self, _: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)
        compressed_frame = payload_in.compressed_frame
        frame_idx = payload_in.frame_index
        frame_height = payload_in.frame_height
        frame_width = payload_in.frame_width

        _logger.info(f'frame_index: {frame_idx}')
        frame = self._decompress_frame_np(compressed_frame, frame_height, frame_width)

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

        payload_out = Payload(
            frame_index=payload_in.frame_index,
            frame_height=resized_frame.shape[0],
            frame_width=resized_frame.shape[1],
            compressed_frame=self._compress_frame_np(resized_frame),
        )

        if self.keep_secondary_frame:
            payload_out.secondary_frame = payload_in.compressed_frame

        yield Message(
            keys=datum.keys,
            value=msgspec.msgpack.encode(payload_out),
        )


if __name__ == '__main__':
    handler = FilterResize()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
