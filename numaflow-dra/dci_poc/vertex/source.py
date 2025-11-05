import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread

import cv2
import numpy as np
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow._constants import STREAM_EOF
from pynumaflow.shared.asynciter import NonBlockingIterator
from pynumaflow.sourcer import (
    AckRequest,
    Message,
    Offset,
    PartitionsResponse,
    PendingResponse,
    ReadRequest,
    SourceAsyncServer,
    Sourcer,
    get_default_partitions,
)

from lib.log import (
    add_new_filehandler,
    set_logger_log_level,
)
from lib.vertex_key_io import (
    VertexKeyIO,
)


class FrameForInput:
    def __init__(self, np_frame: np.ndarray, compressed_frame: bytes):
        self.np_frame = np_frame
        self.compressed_frame = compressed_frame

    def as_raw_frame(self) -> np.ndarray:
        return self.np_frame

    def as_compressed_frame(self) -> bytes:
        return self.compressed_frame

    def height(self) -> int:
        return self.np_frame.shape[0]

    def width(self) -> int:
        return self.np_frame.shape[1]


class AsyncVideoReader(Thread):
    """
    AsyncFileVideoReader load video from source and
    slice a loaded source video into frames with OpenCV.
    Then this Class encode each of them into JPEG and put it in queue.
    It uses a worker thread to read frames asynchronously,
    and a queue to let the caller safely access encoded frames across threads.
    """

    def __init__(self, logger: logging.Logger, failed_read_threshold=30, reconnect_threshold=5):
        Thread.__init__(self)

        self.logger = logger
        self.next_frame_queue = Queue(maxsize=1)
        self.cap = None
        self.failed_read_threshold = failed_read_threshold
        self.reconnect_threshold = reconnect_threshold
        self.is_stream = False
        self.stopped = Event()

        # setup ENV
        load_dotenv(str(Path(__file__).parent / '../../app.env'))
        self.input_type = os.getenv('SOURCE_INPUT_TYPE')
        self.jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))
        if self.input_type is None:
            self.logger.error('environment variable SOURCE_INPUT_TYPE not set')
            sys.exit(1)

        if self.input_type == 'stream':
            self.video_src = os.getenv('VIDEO_STREAM_SRC')
            self.logger.info(f'video_stream_src: {self.video_src}')
            if self.video_src is None:
                self.logger.error('environment variable VIDEO_STREAM_SRC not set')
                sys.exit(1)
        elif self.input_type == 'file':
            self.video_src = os.getenv('VIDEO_FILE_SRC')
            self.logger.info(f'video_file_src: {self.video_src}')
            if self.video_src is None:
                self.logger.error('environment variable VIDEO_FILE_SRC not set')
                sys.exit(1)
        else:
            self.logger.error('environment variable SOURCE_INPUT_TYPE is a file or stream')
            sys.exit(1)

    def run(self) -> None:
        self._open_capture_video()

        if self.input_type == 'stream':
            # assume stream file is infinite
            self.logger.info('AsyncVideoReader: run stream')
            self._run_stream()
        elif self.input_type == 'file':
            # assume video_src is mp4 file
            self.logger.info('AsyncVideoReader: run file')
            self._run_file()
        else:
            self.logger.error("SOURCE_INPUT_TYPE doesn't match the format")
            sys.exit(1)

    def _run_stream(self):
        _reconnect_count = 0
        _failed_read_count = 0

        try:
            while not self.stopped.is_set():
                if self.cap and not self.cap.isOpened():
                    self.logger.error("OpenCV couldn't src file")
                    sys.exit(1)

                ret, raw_frame = self.cap.read()

                if not ret or raw_frame is None:
                    self.logger.info('Failed to read frame')
                    _failed_read_count += 1

                    if _failed_read_count > self.failed_read_threshold:
                        _reconnect_count += 1

                        if _reconnect_count > self.reconnect_threshold:
                            self.logger.error('Reconnect count is over threshold')
                            sys.exit(1)

                        self.logger.info('Trying to reconnect src')
                        self._open_capture_video()
                        self.read_false_count = 0
                else:
                    self.read_false_count = 0

                self.logger.info('Read rightly')
                compressed_frame = self._compress_frame(raw_frame)
                self._put_latest(FrameForInput(raw_frame, compressed_frame))
        finally:
            self.logger.info('_run_stream close')
            self._cap_release()

    def _run_file(self):
        self._show_frame_num()
        # Set the value to 15 fps or higher, ensuring it is visually perceivable
        # # When the value is 20, the actual FPS on the video receiving server is around 10
        fps = 20.0
        frame_period = 1.0 / fps
        t_start = time.monotonic()

        try:
            while not self.stopped.is_set():
                ret, raw_frame = self.cap.read()
                if not ret:
                    self.logger.info('File has ended')
                    # a None means end of file (queue.Queue can accept None)
                    self.next_frame_queue.put(None)
                    return

                self.logger.info('Read rightly')
                compressed_frame = self._compress_frame(raw_frame)

                # Add sleep process to prevent the video from
                # playing too fast to be visually perceivable
                t_process = time.monotonic()
                t_wait = frame_period - (t_process - t_start)
                if t_wait > 0.0:
                    time.sleep(t_wait)

                self._put_latest(FrameForInput(raw_frame, compressed_frame))

                t_start = time.monotonic()
        finally:
            self.logger.info('_run_file close')
            self._cap_release()

    # The stop method is never called because the Sourcer class start method blocks internally
    # Ideally, this method should be called when the gRPC server shuts down,
    # but there's no opportunity to do so due to the blocking nature of Sourcer start()
    def stop(self):
        self.stopped.set()

    def get_next_frame(self) -> FrameForInput | None:
        # Automatically wait in get() until data is put into the queue
        return self.next_frame_queue.get()

    def _open_capture_video(self) -> None:
        self.logger.debug('_open_capture_video')

        # Release previous object
        self._cap_release()

        self.cap = cv2.VideoCapture(self.video_src)

        if not self.cap.isOpened():
            self.logger.error(f'Failed to open video file: {self.video_src}')
            sys.exit(1)

    def _show_frame_num(self) -> None:
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.logger.info(f'Total frame: {frame_count}')

    def _compress_frame(self, frame: np.array) -> bytes:
        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ret:
            self.logger.error('Failed to compress frame to jpg')
            sys.exit(1)

        return buf.tobytes()

    def _put_latest(self, item: FrameForInput):
        try:
            self.next_frame_queue.put_nowait(item)
        except Full:
            try:  # noqa: SIM105
                self.next_frame_queue.get_nowait()  # drop a queued frame
            except Empty:
                pass
            try:  # noqa: SIM105
                self.next_frame_queue.put_nowait(item)
            except Full:
                pass

    def _cap_release(self):
        if self.cap:
            self.cap.release()


class AsyncSourceSendFrame(Sourcer):
    """AsyncSource is a class for User Defined Source implementation."""

    def __init__(self):
        load_dotenv(str(Path(__file__).parent / '../../app.env'))

        # setup logger
        self.logger = setup_logging('console_logger')
        log_path = os.getenv('LOG_PATH')
        log_file = os.path.join(log_path, 'source.log')
        add_new_filehandler(self.logger, log_file)
        set_logger_log_level(self.logger)
        self.logger.info('Source init')

        self.async_video_reader = AsyncVideoReader(self.logger)
        self.async_video_reader.start()

        """
        to_ack_set: Set to maintain a track of the offsets yet to be acknowledged
        read_idx : the offset idx till where the messages have been read.
                   use this field as frame_index.
        """
        self.to_ack_set = set()
        self.read_idx = 0

    async def read_handler(self, datum: ReadRequest, output: NonBlockingIterator):
        """read_handler is used to read the data from the source and send the data forward
        for each read request we process num_records and increment the read_idx to indicate that
        the message has been read and the same is added to the ack set
        """
        if self.to_ack_set:
            return

        # self.logger.debug('datum.num_records: %d', datum.num_records)
        for _x in range(datum.num_records):
            headers = {'x-txn-id': str(uuid.uuid4())}

            vk_io = VertexKeyIO()
            frame = self.async_video_reader.get_next_frame()
            if frame is None:
                self.logger.info('A None frame was passed. src_file has ended')
                self.async_video_reader.join()
                await output.put(STREAM_EOF)
                break

            # self._debug_frame_info(frame.as_raw_frame())

            vk_io.add('frame_idx', self.read_idx)
            vk_io.add('org_height', frame.height())
            vk_io.add('org_width', frame.width())

            await output.put(
                Message(
                    payload=frame.as_compressed_frame(),
                    offset=Offset.offset_with_default_partition_id(str(self.read_idx).encode()),
                    event_time=datetime.now(),
                    keys=vk_io.keys_list,
                    headers=headers,
                ),
            )
            self.to_ack_set.add(str(self.read_idx))
            self.read_idx += 1

    async def ack_handler(self, ack_request: AckRequest):
        """The ack handler is used acknowledge the offsets that have been read, and remove them
        from the to_ack_set
        """
        for req in ack_request.offsets:
            self.to_ack_set.remove(str(req.offset, 'utf-8'))

    async def pending_handler(self) -> PendingResponse:
        """The simple source always returns zero to indicate there is no pending record."""
        return PendingResponse(count=0)

    async def partitions_handler(self) -> PartitionsResponse:
        """The simple source always returns default partitions."""
        return PartitionsResponse(partitions=get_default_partitions())

    def _debug_frame_info(self, frame: np.ndarray) -> None:
        height, width, channels = frame.shape
        data_type = frame.dtype

        # calculate data size of frame(Byte unit of Numpy)
        data_size_bytes = frame.nbytes

        self.logger.debug(f'frame size: {width} x {height}')
        self.logger.debug(f'channels  : {channels}')
        self.logger.debug(f'data type : {data_type}')
        self.logger.debug(
            f'data size : {data_size_bytes} Byte ({data_size_bytes / 1024:.2f} KB), '
            f'({data_size_bytes / (1024 * 1024):.2f} MB)',
        )

    def stop_reader(self):
        self.async_video_reader.stop()


if __name__ == '__main__':
    handler = AsyncSourceSendFrame()
    grpc_server = SourceAsyncServer(handler)
    grpc_server.start()
