import pickle
import os
import sys
import subprocess

import uuid
from datetime import datetime

from dotenv import load_dotenv
import cv2
import numpy as np

sys.path.append("../log")
from log import (
    setup_logger,
    set_logger_log_level,
    add_new_filehandler,
)

from pynumaflow.shared.asynciter import NonBlockingIterator
from pynumaflow.sourcer import (
    ReadRequest,
    Message,
    AckRequest,
    PendingResponse,
    Offset,
    PartitionsResponse,
    get_default_partitions,
    Sourcer,
    SourceAsyncServer,
)

load_dotenv("../system-config.env")


def capture_video() -> any:

    video_src = os.getenv("VIDEO_SRC")
    if not os.path.exists(video_src):
        logger.error(f"Video file does not exist: {video_src}")
        sys.exit(1)

    cap = cv2.VideoCapture(video_src)

    if not cap.isOpened():
        logger.error(f"Failed to open video file: {video_src}")
        sys.exit(1)

    return cap


def debug_frame_info(frame: np.ndarray) -> None:
    height, width, channels = frame.shape
    data_type = frame.dtype

    # calculate data size of frame(Byte unit of Numpy)
    data_size_bytes = frame.nbytes

    logger.debug(f"frame size: {width} x {height}")
    logger.debug(f"channels  : {channels}")
    logger.debug(f"data type : {data_type}")
    logger.debug(f"data size : {data_size_bytes} Byte ({data_size_bytes / 1024:.2f} KB), ({data_size_bytes / (1024*1024):.2f} MB)")


class AsyncSourceSendFrame(Sourcer):
    """
    AsyncSource is a class for User Defined Source implementation.
    """

    def __init__(self):
        """
        to_ack_set: Set to maintain a track of the offsets yet to be acknowledged
        read_idx : the offset idx till where the messages have been read. use this field as frame_index.
        """
        self.to_ack_set = set()
        self.read_idx = 0
        self.cap = None

    async def read_handler(self, datum: ReadRequest, output: NonBlockingIterator):
        """
        read_handler is used to read the data from the source and send the data forward
        for each read request we process num_records and increment the read_idx to indicate that
        the message has been read and the same is added to the ack set
        """
        if self.to_ack_set:
            return

        if self.cap is None:
            self.cap = capture_video()
            frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            logger.info(f"total frame: {frame_count}")

        for x in range(datum.num_records):
            headers = {"x-txn-id": str(uuid.uuid4())}

            ret, frame = self.cap.read()
            if ret == False:
                break

            # debug_frame_info(frame)
            
            await output.put(
                Message(
                    payload = pickle.dumps(frame),
                    offset=Offset.offset_with_default_partition_id(str(self.read_idx).encode()),
                    event_time=datetime.now(),
                    keys = [
                        str(self.read_idx),  # frame_index
                        str(frame.shape[0]), # original_height
                        str(frame.shape[1])  # original_width
                    ],
                    headers=headers,
                )
            )
            self.to_ack_set.add(str(self.read_idx))
            self.read_idx += 1
        

    async def ack_handler(self, ack_request: AckRequest):
        """
        The ack handler is used acknowledge the offsets that have been read, and remove them
        from the to_ack_set
        """
        for req in ack_request.offsets:
            self.to_ack_set.remove(str(req.offset, "utf-8"))

    async def pending_handler(self) -> PendingResponse:
        """
        The simple source always returns zero to indicate there is no pending record.
        """
        return PendingResponse(count=0)

    async def partitions_handler(self) -> PartitionsResponse:
        """
        The simple source always returns default partitions.
        """
        return PartitionsResponse(partitions=get_default_partitions())

    def __del__(self):
        if self.cap:
            self.cap.release()


if __name__ == "__main__":
    global logger
    logger = setup_logger("console_logger")
    add_new_filehandler(logger, "/var/log/numaflow/source.log")
    set_logger_log_level(logger)

    handler = AsyncSourceSendFrame()
    grpc_server = SourceAsyncServer(handler)
    logger.info(f"grpc server start")
    grpc_server.start()

    logger.info(f"grpc server end")
