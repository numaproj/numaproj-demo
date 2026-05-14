import os
import sys
from collections.abc import AsyncIterable
from pathlib import Path

import cv2
import msgspec
import numpy as np
import torch
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import Datum, MapStreamAsyncServer, MapStreamer, Message

# this .py file need Official-YOLOv7(https://github.com/WongKinYiu/yolov7))
# in the same directory
sys.path.append(str(Path(__file__).parent / '../../ml-models/official-yolov7'))
from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.general import check_img_size, non_max_suppression, scale_coords

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.message_spec import BoundingBox, Payload


class Infer(MapStreamer):
    def __init__(self):
        # setup logger
        self.logger = setup_logging('console_logger')
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'inference.log')
        add_new_filehandler(self.logger, log_file)
        set_logger_log_level(self.logger)
        self.logger.info('Infer init')

        self.check_gpu_info()

        # setup yolov7
        self.setup_yolov7_model(
            (Path(__file__).parent / './../../ml-models/official-yolov7/yolov7.pt').resolve(
                strict=True
            ),
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

    def setup_yolov7_model(
        self,
        weight_path: Path,
    ) -> None:
        """
        1. specify device to execute model
        2. verify weight file path
        3. load model
        4. switch model to inference(eval) mode
        5. get class name
        """
        try:
            # 1. specify device to execute model
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

            # 2. load model
            self.logger.info(f'weight_path: {weight_path}')
            self.model = attempt_load(str(weight_path), map_location=self.device)  # load FP32 model

            # 3. switch model to inference(eval) mode
            self.model.eval()

            # 4. get class name
            self.names = (
                self.model.module.names if hasattr(self.model, 'module') else self.model.names
            )
        except Exception as e:
            self.logger.error(f'Encountered exception: {e} in setup Yolov7 model', exc_info=True)

        self.logger.info('Setup Yolov7 model completed')

    def preprocess_image(self, img: np.ndarray) -> torch.Tensor:
        """
        1. adjust image size according to the stride
        2. padding for inference
        3. BGR -> RGB, HWC -> CHW
        4. convert to tensor & normalize & transfer it to device
        5. add batch dimension
        6. (option) if model can receive FP16, cast input data to FP16
        """
        # 1. adjust image size according to the stride
        stride = int(
            self.model.stride.max()
        )  # model stride, step size for sliding the convolution filter
        img_size = check_img_size(
            int(img.shape[1]), s=stride
        )  # check img_size. img.shape[1] is row.

        # 2. padding for inference
        img = letterbox(img, new_shape=img_size, stride=stride)[0]

        # 3. BGR(OpenCV) -> RGB(Yolo), Memory Layout: HWC -> CHW(PyTorch)
        img = img[:, :, ::-1].transpose(2, 0, 1)  # transform array format
        img = np.ascontiguousarray(img)  # make data memory-contiguous

        # 4. convert to tensor & normalize & transfer it to device
        tensor = (torch.from_numpy(img) / 255.0).to(self.device).float()

        # 5. add batch dimension. (C, H, W) -> (1, C, H, W)
        if tensor.ndimension() == 3:
            tensor = tensor.unsqueeze(0)

        # (option) if model can receive FP16, cast input data to FP16
        if getattr(self.model, 'dtype', torch.float32) == torch.float16:
            tensor = tensor.half()

        return tensor  # (1, 3, H, W) on device(cuda)

    def infer(self, input_tensor, org_img) -> list[dict]:
        try:
            # inference
            with torch.torch.inference_mode():
                pred = self.model(input_tensor)[0]

            # post processing
            # remove overlap bbox with NMS
            ## conf_thres: under limit of confidence threshold.
            ## iou_thres : threshold of intersection over Union
            pred = non_max_suppression(pred, conf_thres=0.25, iou_thres=0.45)
            self.logger.debug(f'prediction: {pred}')
            # pred is "raw prediction", [N, 85]. In the case where the dataset is COCO80
            # N: Number of candidate boxes generated during inference
            # 85: [cx, cy, w, h, confidence score, cls1, ..., cls80]
            # cx, cy: center coordinates

            results: list[dict] = []
            for det in pred:  # det: detection tensor
                if det is None or len(det) == 0:
                    continue

                # Convert the coordinate system back to the original image coordinates.
                # - remove padding
                # - convert from center coordinate format to rectangle format
                det[:, :4] = scale_coords(
                    input_tensor.shape[2:],  # (H, W): image size used for inference
                    det[:, :4],  # (cx, cy, w, h)
                    org_img.shape,  # (H, W, C)
                ).round()

                for *xyxy, conf, cls in det:
                    results.append(
                        {
                            'bbox': [float(e) for e in xyxy],  # x1, y1, x2, y2
                            'conf': float(conf),
                            'class': self.names[int(cls)],
                        }
                    )
            self.logger.info(f'results: {results}')

            return results
        except Exception as e:
            self.logger.error(f'Encountered exception: {e} in infer()', exc_info=True)

    def _decompress_frame_np(self, value: bytes) -> np.ndarray:
        if not value:
            self.logger.error('Empty payload received')
            return None

        arr = np.frombuffer(value, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            self.logger.error(f'cv2.imdecode failed: buffer_len={len(value)}')

        return img

    async def handler(self, _keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        payload_in = msgspec.msgpack.decode(datum.value, type=Payload)

        # The resized_frame_bgr is a BGR image but YOLOv7 takes an RGB one.
        # Color conversion will be done in the preprocess_image method later.
        resized_frame_bgr = self._decompress_frame_np(payload_in.compressed_frame)
        height = resized_frame_bgr.shape[0]
        width = resized_frame_bgr.shape[1]

        _ = datum.event_time
        _ = datum.watermark

        # inference data on GPU
        frame_idx = payload_in.frame_index
        self.logger.info(f'frame_index: {frame_idx}')
        self.logger.debug(f'resized_frame_bgr: {resized_frame_bgr}')

        input_tensor = self.preprocess_image(resized_frame_bgr)
        res = self.infer(input_tensor, resized_frame_bgr)

        # The Objects included in the dataset are not being detected
        # bboxes is [[]]
        if len(res) == 1 and isinstance(res[0], list) and len(res[0]) == 0:
            yield Message.to_drop()
            return

        payload_out = Payload(
            frame_index=payload_in.frame_index,
            original_height=payload_in.original_height,
            original_width=payload_in.original_width,
        )

        for r in res:
            payload_out.bounding_boxes.append(
                BoundingBox(
                    confidence=float(r['conf']),
                    class_id=str(r['class']),
                    top_left_x=float(r['bbox'][0]) / float(width),
                    top_left_y=float(r['bbox'][1]) / float(height),
                    bottom_right_x=float(r['bbox'][2]) / float(width),
                    bottom_right_y=float(r['bbox'][3]) / float(height),
                )
            )
        self.logger.debug(f'{payload_out}')

        # str_size = 0
        # for s in vk_io.keys_list:
        #    self.logger.debug(f'{s}')
        #    str_size += sys.getsizeof(s)
        # self.logger.debug(f'{sys.getsizeof(pickle.dumps(resized_frame))}')
        # self.logger.debug(f'{str_size}')

        yield Message(value=msgspec.msgpack.encode(payload_out))


if __name__ == '__main__':
    handler = Infer()
    grpc_server = MapStreamAsyncServer(handler)
    grpc_server.start()
