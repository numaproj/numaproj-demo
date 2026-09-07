import os
import sys
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

import cv2
import msgspec
import numpy as np
import torch
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message

# this .py file need pytorch-YOLOv4(https://github.com/Tianxiaomo/pytorch-YOLOv4/tree/master))
# in the same directory
sys.path.append(str(Path(__file__).parent / '../../ml-models/pytorch-YOLOv4'))
from models import Yolov4
from tool.torch_utils import do_detect
from tool.utils import load_class_names

from lib.log import setup_logging
from lib.message_spec import BoundingBox, Payload

_logger = None


def setup_logger():
    global _logger
    if _logger is None:
        _logger = setup_logging(__name__)


class Infer(MapStreamer):
    def __init__(self):
        setup_logger()
        self.keep_secondary_frame = int(os.getenv('KEEP_SECONDARY_FRAME', '0')) != 0
        _logger.info('Inference (YOLOv4) initialized')

        self.check_gpu_info()

        # setup yolov4
        self.model: Yolov4 | None = None
        self.setup_yolov4_model(
            str(Path(__file__).parent / './../../ml-models/pytorch-YOLOv4/yolov4.conv137.pth'),
            str(Path(__file__).parent / './../../ml-models/pytorch-YOLOv4/yolov4.pth'),
            80,
            str(Path(__file__).parent / './../../ml-models/pytorch-YOLOv4/data/coco.names'),
        )

    def check_gpu_info(self):
        _logger.info(f'torch cuda version: {torch.version.cuda}')
        if torch.cuda.is_available():
            _logger.info('Available GPU(s):')
            for i in range(torch.cuda.device_count()):
                gpu = torch.cuda.get_device_properties(i)
                _logger.info(f'GPU {i}: {gpu.name}, {gpu.total_memory / 1e9} GB')
        else:
            _logger.info('No Available GPU')
            sys.exit(1)

    def setup_yolov4_model(
        self,
        conv137weight: str | None,
        weightfile: str | None,
        n_classes: int | None,
        namesfile: str | None,
    ) -> None:
        try:
            # https://github.com/Tianxiaomo/pytorch-YOLOv4/blob/a65d219f9066bae4e12003bd7cdc04531860c672/models.py#L409
            self.model = Yolov4(
                yolov4conv137weight=conv137weight,
                n_classes=n_classes,
                inference=True,
            )
            pretrained_dict = torch.load(weightfile)
            self.model.load_state_dict(pretrained_dict, strict=False)
            self.model.eval()
            self.model.to(torch.device('cuda'))

            self.class_names = load_class_names(namesfile)
        except Exception as e:
            _logger.error(f'Encountered exception: {e} in setup YOLOv4 model', exc_info=True)
            return False

        _logger.info('Setup YOLOv4 model completed')
        return True

    def infer(self, frame) -> list[Any] | None:
        try:
            bboxes = do_detect(
                model=self.model,
                img=frame,
                conf_thresh=0.3,
                nms_thresh=0.45,
                use_cuda=1,
            )

            return bboxes
        except Exception as e:
            _logger.error(f'Encountered exception: {e} in infer()', exc_info=True)
            return None

    def _decompress_frame_np(self, value: bytes) -> np.ndarray:
        if not value:
            _logger.error('Empty payload received')
            return None

        arr = np.frombuffer(value, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            _logger.error(f'cv2.imdecode failed: buffer_len={len(value)}')

        return img

    async def handler(self, _keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)
        resized_frame_bgr = self._decompress_frame_np(payload_in.compressed_frame)

        # Note: YOLOv4's model takes an RGB (not a BGR) image but we do not
        # need to convert color of the resized_frame_bgr because the
        # function do_detect (called by self.infer) does that conversion.
        # So what we have to do is only giving a BGR image to the do_detect.

        _ = datum.event_time
        _ = datum.watermark

        # inference data on GPU
        frame_idx = payload_in.frame_index
        _logger.debug(f'Frame index: {frame_idx}')
        bboxes = self.infer(resized_frame_bgr)
        _logger.debug(f'Inference results: {bboxes}')

        payload_out = Payload(frame_index=payload_in.frame_index)

        if len(bboxes) == 1 and isinstance(bboxes[0], list) and len(bboxes[0]) == 0:
            pass
        else:
            # Output only the first bounding box to emphasize the difference
            # of the YOLOv4 and the YOLOv7 pipelines.
            payload_out.bounding_boxes.append(
                BoundingBox(
                    confidence=float(bboxes[0][0][4]),
                    class_id=int(bboxes[0][0][6]),
                    top_left_x=float(bboxes[0][0][0]),
                    top_left_y=float(bboxes[0][0][1]),
                    bottom_right_x=float(bboxes[0][0][2]),
                    bottom_right_y=float(bboxes[0][0][3]),
                )
            )

        if self.keep_secondary_frame:
            payload_out.compressed_frame = payload_in.secondary_frame

        yield Message(
            keys=datum.keys,
            value=msgspec.msgpack.encode(payload_out),
        )


if __name__ == '__main__':
    handler = Infer()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
