import asyncio
import json
import os
import threading
import time
from datetime import UTC, datetime

import cv2
import grpc
import numpy as np
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from pynumaflow import setup_logging
from pynumaflow.info.types import EOF
from pynumaflow.mapstreamer.servicer.async_servicer import AsyncMapStreamServicer
from pynumaflow.proto.mapper import map_pb2_grpc
from pynumaflow.proto.sinker import sink_pb2_grpc
from pynumaflow.proto.sourcer import source_pb2_grpc
from pynumaflow.sinker.servicer.async_servicer import AsyncSinkServicer
from pynumaflow.sourcer.servicer.async_servicer import AsyncSourceServicer

_logger = setup_logging(__name__)

# === Stub ===


def _run_loop_forever(loop: asyncio.AbstractEventLoop) -> None:
    """
    Target Function: continue to run event loop in sub thread
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()


def start_event_loop_thread(
    name: str = 'grpc-loop',
) -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    """
    - Start thread and create event loop that was executed in this thread
    - event loop will be used with a gRPC server
    """
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=_run_loop_forever, args=(loop,), name=name, daemon=True)
    thread.start()
    return loop, thread


def stop_event_loop_thread(loop, thread):
    """
    - stop event loop
    - join thread
    - close event loop
    """
    try:
        loop.call_soon_threadsafe(loop.stop)
    except Exception as e:
        _logger.warning('failed to stop loop thread: %s', e)

    try:
        # avoid self-join
        if threading.current_thread() is not thread:
            thread.join(timeout=3)
        else:
            _logger.warning('skip joining the same thread to avoid deadlock')
    except Exception as e:
        _logger.warning('failed to join loop thread: %s', e)

    try:
        loop.close()
    except Exception as e:
        _logger.warning('failed to close loop: %s', e)


def _prepare_unix_socket(socket: str):
    if socket.startswith('unix://'):
        path = socket[len('unix://') :]
        try:
            if os.path.exists(path):
                os.unlink(path)
        except FileNotFoundError:
            pass


async def start_source_server(socket: str, udf: AsyncSourceServicer) -> grpc.aio.Server:
    """
    Note: This function will be called and executed in asyncio.run_coroutin_threadsafe
    """
    server = grpc.aio.server()
    source_pb2_grpc.add_SourceServicer_to_server(udf, server)

    _prepare_unix_socket(socket)
    if server.add_insecure_port(socket) == 0:
        msg = f'Failed to bind gRPC server to : {socket}'
        raise RuntimeError(msg)

    await server.start()
    return server


async def start_map_server(socket: str, udf: AsyncMapStreamServicer) -> grpc.aio.Server:
    """
    Note: This function will be called and executed in asyncio.run_coroutin_threadsafe
    """
    server = grpc.aio.server()
    map_pb2_grpc.add_MapServicer_to_server(udf, server)

    _prepare_unix_socket(socket)
    if server.add_insecure_port(socket) == 0:
        msg = f'Failed to bind gRPC server to : {socket}'
        raise RuntimeError(msg)

    await server.start()
    return server


async def start_sink_server(socket: str, udf: AsyncSinkServicer) -> grpc.aio.Server:
    """
    Note: This function will be called and executed in asyncio.run_coroutin_threadsafe
    """
    server = grpc.aio.server()
    sink_pb2_grpc.add_SinkServicer_to_server(udf, server)

    _prepare_unix_socket(socket)
    if server.add_insecure_port(socket) == 0:
        msg = f'Failed to bind gRPC server to : {socket}'
        raise RuntimeError(msg)

    await server.start()
    return server


async def stop_source_server(server: grpc.aio.Server, grace: float = 1.0):
    await server.stop(grace=grace)


async def stop_map_server(server: grpc.aio.Server, grace: float = 1.0):
    await server.stop(grace=grace)


async def stop_sink_server(server: grpc.aio.Server, grace: float = 1.0):
    await server.stop(grace=grace)


def wait_for_channnel_ready(
    socket: str, total_timeout: float = 10.0, initial_backoff: float = 0.2, max_backoff: float = 2.0
) -> grpc.Channel:
    deadline = time.monotonic() + total_timeout
    backoff = initial_backoff

    channel = grpc.insecure_channel(socket)

    attempt = 1
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            channel.close()
            msg = f'gRPC channel not ready within {total_timeout:.1f}s (target={socket})'
            raise TimeoutError(msg)

        try:
            wait = min(total_timeout, max(0.05, remaining))
            grpc.channel_ready_future(channel).result(timeout=wait)
            # When success, result() only return None. Reaching here is success.
            _logger.info('gRPC channel ready (target=%s, attempts=%d)', socket, attempt)
            return channel

        except grpc.FutureTimeoutError as e:
            _logger.warning(
                'Channel not ready yet (attempt=%d, will backoff %.2fs): %s', attempt, backoff, e
            )

            sleep_for = min(backoff, max(0.0, deadline - time.monotonic()))
            if sleep_for > 0:
                time.sleep(sleep_for)
            backoff = min(max_backoff, backoff * 2.0)

        attempt += 1


# ============


def compress_frame(frame: np.ndarray) -> bytes:
    ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret:
        raise RuntimeError
    return buf.tobytes()


# return np array as if use cv2.VideoCapture().read()
# color space is BGR in CV2
def mock_4k_frame():
    frame = np.full((2160, 3840, 3), (0, 0, 255), dtype=np.uint8)
    return frame


def get_time_args() -> (datetime, datetime):
    event_time_timestamp = _timestamp_pb2.Timestamp()
    event_time_timestamp.FromDatetime(dt=mock_event_time())
    watermark_timestamp = _timestamp_pb2.Timestamp()
    watermark_timestamp.FromDatetime(dt=mock_watermark())
    return event_time_timestamp, watermark_timestamp


def mock_message():
    msg = bytes('test_mock_message', encoding='utf-8')
    return msg


def mock_event_time():
    t = datetime.fromtimestamp(1662998400, UTC)
    return t


def mock_new_event_time():
    t = datetime.fromtimestamp(1663098400, UTC)
    return t


def mock_watermark():
    t = datetime.fromtimestamp(1662998460, UTC)
    return t


def mock_headers():
    headers = {'key1': 'value1', 'key2': 'value2'}
    return headers


def mock_interval_window_start():
    event_time_timestamp = _timestamp_pb2.Timestamp()
    t = datetime.fromtimestamp(1662998400000 / 1e3, UTC)
    event_time_timestamp.FromDatetime(dt=t)
    # t = datetime.fromtimestamp(1662998400000, UTC)
    return event_time_timestamp


def mock_interval_window_end():
    event_time_timestamp = _timestamp_pb2.Timestamp()
    t = datetime.fromtimestamp(1662998460000 / 1e3, UTC)
    event_time_timestamp.FromDatetime(dt=t)
    # t = datetime.fromtimestamp(1662998460000, UTC)
    return event_time_timestamp


def mock_start_time():
    t = datetime.fromtimestamp(1662998400, UTC)
    return t


def mock_end_time():
    t = datetime.fromtimestamp(1662998520, UTC)
    return t


def read_info_server(info_file: str):
    f = open(info_file)
    retry = 10
    res = f.read()
    a, b = info_serv_is_ready(info_serv_data=res)
    while (a is not True) and retry > 0:
        a, b = info_serv_is_ready(info_serv_data=res)

    a, b = info_serv_is_ready(info_serv_data=res)
    if a:
        res = json.loads(b)
        return res

    return None


def info_serv_is_ready(info_serv_data: str, eof: str = EOF):
    if len(info_serv_data) < len(eof):
        return False
    len_diff = len(info_serv_data) - len(eof)
    last_char = info_serv_data[len_diff:]
    if last_char == EOF:
        data = info_serv_data[:len_diff]
        return True, data
    return False, None


def mock_terminate_on_stop(process):
    _logger.info('Mock terminate %s', str(process))
