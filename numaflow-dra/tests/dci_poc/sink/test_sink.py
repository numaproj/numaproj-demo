import logging
import sys

import grpc
import numpy as np
import pytest
from pynumaflow import setup_logging
from pynumaflow.proto.sinker import sink_pb2_grpc
from pynumaflow.sinker import SinkAsyncServer
from tests.dci_poc.sink.utils import request_generator

from dci_poc.vertex.sink import AsyncSink

logger = setup_logging(__name__)


class FrameCapture:
    def __init__(self):
        self.frames: list[tuple[int, np.ndarray, np.ndarray]] = []

    def __call__(self, frame_idx: int, resized_frame: np.ndarray, overlay_frame: np.ndarray):
        self.frames.append((frame_idx, resized_frame, overlay_frame))


@pytest.fixture
def capture_func() -> FrameCapture:
    return FrameCapture()


@pytest.fixture
def sink_servicer_impl(capture_func) -> sink_pb2_grpc.SinkServicer:
    handler = AsyncSink(capture_func)
    server = SinkAsyncServer(handler)
    udf = server.servicer
    return udf


def test_sink(capture_func, sink_stub) -> None:
    generator_response = None
    try:
        generator_response = sink_stub.SinkFn(
            request_iterator=request_generator(count=1, session=1)
        )
    except grpc.RpcError as e:
        logging.exception(e)

    handshake = next(generator_response)
    # assert that handshake response is received.
    assert handshake.handshake.sot

    data_resp = []
    for r in generator_response:
        data_resp.append(r)

    # response + EOT
    assert len(data_resp) == 2

    # check vertex response
    idx = 0
    while idx < len(data_resp) - 1:
        assert len(data_resp[idx].results) == 1
        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot

    assert capture_func.frames is not None
    assert len(capture_func.frames) >= 1

    for frame in capture_func.frames:
        idx, resized_frame, overlay_frame = frame

        assert resized_frame is not None
        assert overlay_frame is not None

        # check frame size
        assert resized_frame.shape[0] == overlay_frame.shape[0]
        assert resized_frame.shape[1] == overlay_frame.shape[1]
        assert resized_frame.shape[2] == overlay_frame.shape[2]

        h, w = overlay_frame.shape[:2]
        green_px = 0
        for y in range(h):
            for x in range(w):
                # pick differences pixel
                if (
                    overlay_frame[y][x][0] != resized_frame[y][x][0]
                    or overlay_frame[y][x][1] != resized_frame[y][x][1]
                    or overlay_frame[y][x][2] != resized_frame[y][x][2]
                ):
                    # check green for differences (bbox)
                    assert overlay_frame[y][x][0] == 0
                    assert overlay_frame[y][x][1] == 255
                    assert overlay_frame[y][x][2] == 0
                    green_px += 1

        # check bbox line pixel count
        # depends on the formula in sink.py
        thickness = max(1, int(min(h, w) / 200))
        max_bbox_lin_px = ((h + w) * 2 * thickness) - (thickness * thickness * 4)
        assert max_bbox_lin_px >= green_px


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
