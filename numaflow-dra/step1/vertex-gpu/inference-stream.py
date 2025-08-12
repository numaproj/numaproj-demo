import os
import sys
import pickle
import time

from dotenv import load_dotenv
import torch
from typing import Optional, Any

from collections.abc import AsyncIterable
from pynumaflow.mapstreamer import Message, Datum, MapStreamAsyncServer, MapStreamer

# this .py file need pytorch-YOLOv4(https://github.com/Tianxiaomo/pytorch-YOLOv4/tree/master)) in the same directory
sys.path.append("../../pytorch-YOLOv4")
from models import Yolov4
from tool.utils import load_class_names
from tool.torch_utils import do_detect

sys.path.append("../../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

load_dotenv("../../system-config.env")

class Infer(MapStreamer):
    def __init__(self, ):
        self.model: Optional[Yolov4] = None
        self.setup_yolov4_model(
            "./../../pytorch-YOLOv4/yolov4.conv137.pth",
            "./../../pytorch-YOLOv4/yolov4.pth",
            80,
            "./../../pytorch-YOLOv4/data/coco.names",
        )

    def setup_yolov4_model(
        self,
        conv137weight: Optional[str],
        weightfile: Optional[str],
        n_classes: Optional[int],
        namesfile: Optional[str],
    ) -> None:

        try:
            # https://github.com/Tianxiaomo/pytorch-YOLOv4/blob/a65d219f9066bae4e12003bd7cdc04531860c672/models.py#L409
            self.model = Yolov4(yolov4conv137weight=conv137weight, n_classes=n_classes, inference=True)
            pretrained_dict = torch.load(weightfile)
            self.model.load_state_dict(pretrained_dict, strict=False)
            self.model.eval()
            self.model.to(torch.device('cuda'))
            
            self.class_names = load_class_names(namesfile)
        except Exception as e:
            logger.error(f"Encountered exception: {e} in setup Yolov4 model", exc_info=True)
            return False

        logger.info(f"Setup Yolov4 model completed")
        return True


    def infer(self, frame) -> Optional[list[Any]]:
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
            logger.error(f"Encountered exception: {e} in infer()", exc_info=True)
            return None


    async def handler(self, keys: list[str], datum: Datum) -> AsyncIterable[Message]:
        
        resized_frame = pickle.loads(datum.value, encoding="bytes")
        _ = datum.event_time
        _ = datum.watermark

        # inference data on GPU
        logger.info(f"frame_index: {datum._keys[0]}")
        logger.debug(f"resized_frame: {resized_frame}")
        bboxes = self.infer(resized_frame)
        logger.info(f"infer_result: {bboxes}")

        # The Objects included in the dataset are not being detected
        # bboxes is [[]]
        if len(bboxes) == 1 and isinstance(bboxes[0], list) and len(bboxes[0]) == 0:
            yield Message.to_drop()
            return
        
        yield Message(
            value = pickle.dumps(bboxes),
            keys = [
                str(datum._keys[0]), # frame_index
                str(datum._keys[1]), # original_height
                str(datum._keys[2]), # original_width
            ]
        )

def check_gpu_info():
    logger.info(f"torch cuda version: {torch.version.cuda}")
    if torch.cuda.is_available():
        logger.info(f"Available GPU is following")
        for i in range(torch.cuda.device_count()):
            gpu = torch.cuda.get_device_properties(i)
            logger.info(f"GPU {i}: {gpu.name}, {gpu.total_memory / 1e9} GB")
    else:
        logger.info("Available GPU is nothing")
        sys.exit(1)


if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    add_new_filehandler(logger, "/var/log/numaflow/inference.log")
    set_logger_log_level(logger)
    
    check_gpu_info()

    handler = Infer()
    grpc_server = MapStreamAsyncServer(handler)
    logger.info(f"grpc server start")
    grpc_server.start()