import os
import sys
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message

# this .py file need pytorch-YOLOv4(https://github.com/Tianxiaomo/pytorch-YOLOv4/tree/master))
# in the same directory
sys.path.append(str(Path(__file__).parent / '../../ml-models/pytorch-YOLOv4'))
from models import Yolov4
from tool.torch_utils import do_detect
from tool.utils import load_class_names

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.vertex_key_io import (
    VertexKeyIO,
)


class Infer(MapStreamer):
    def __init__(self):
        load_dotenv(str(Path(__file__).parent / '../../app.env'))

        # setup logger
        self.logger = setup_logging('console_logger')
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'inference.log')
        add_new_filehandler(self.logger, log_file)
        set_logger_log_level(self.logger)
        self.logger.info('Infer init')

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
        self.logger.info(f'torch cuda version: {torch.version.cuda}')
        if torch.cuda.is_available():
            self.logger.info('Available GPU is following')
            for i in range(torch.cuda.device_count()):
                gpu = torch.cuda.get_device_properties(i)
                self.logger.info(f'GPU {i}: {gpu.name}, {gpu.total_memory / 1e9} GB')
        else:
            self.logger.info('Available GPU is nothing')
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
            self.logger.error(f'Encountered exception: {e} in setup Yolov4 model', exc_info=True)
            return False

        self.logger.info('Setup Yolov4 model completed')
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
            self.logger.error(f'Encountered exception: {e} in infer()', exc_info=True)
            return None

    def _decompress_frame_np(self, value: bytes) -> np.ndarray:
        if not value:
            self.logger.error('Empty payload received')
            return None

        arr = np.frombuffer(value, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)

        if img is None:
            self.logger.error(f'cv2.imdecode failed: buffer_len={len(value)}')

        return img

    async def handler(self, _keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        resized_frame = self._decompress_frame_np(datum.value)

        _ = datum.event_time
        _ = datum.watermark

        vk_io = VertexKeyIO(datum.keys)

        # inference data on GPU
        frame_idx = vk_io['frame_idx']
        self.logger.info(f'frame_index: {frame_idx}')
        self.logger.debug(f'resized_frame: {resized_frame}')
        bboxes = self.infer(resized_frame)
        self.logger.info(f'infer_result: {bboxes}')

        # The Objects included in the dataset are not being detected
        # bboxes is [[]]
        if len(bboxes) == 1 and isinstance(bboxes[0], list) and len(bboxes[0]) == 0:
            yield Message.to_drop()
            return

        vk_io.add('box_len', len(bboxes))
        # fmt: off
        for i, box in enumerate(bboxes):
            vk_io.add(f'box_{i}_confidence',   box[i][4])
            vk_io.add(f'box_{i}_class_id',     box[i][6])
            vk_io.add(f'box_{i}_LeftUpX',      box[i][0])
            vk_io.add(f'box_{i}_LeftUpY',      box[i][1])
            vk_io.add(f'box_{i}_RightDownX',   box[i][2])
            vk_io.add(f'box_{i}_RightDownY',   box[i][3])
        self.logger.debug(f'{vk_io.items()}')
        # fmt: on

        # str_size = 0
        # for s in vk_io.keys_list:
        #    self.logger.debug(f'{s}')
        #    str_size += sys.getsizeof(s)
        # self.logger.debug(f'{sys.getsizeof(pickle.dumps(resized_frame))}')
        # self.logger.debug(f'{str_size}')

        yield Message(
            value=datum.value,
            keys=vk_io.keys_list,
        )


if __name__ == '__main__':
    handler = Infer()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
