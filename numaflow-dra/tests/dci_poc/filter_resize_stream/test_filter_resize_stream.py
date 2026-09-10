import logging
import os
import sys

import cv2
import grpc
import msgspec
import numpy as np
import pytest
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import MapStreamAsyncServer
from pynumaflow.mapstreamer.servicer.async_servicer import AsyncMapStreamServicer
from tests.dci_poc.filter_resize_stream.utils import request_generator

from dci_poc.vertex_gpu_fr.filter_resize_stream import FilterResize
from lib.message_spec import Payload

logger = setup_logging(__name__)


@pytest.fixture
def map_servicer_impl() -> AsyncMapStreamServicer:
    handler = FilterResize()
    server = MapStreamAsyncServer(handler)
    udf = server.servicer
    return udf


def test_filter_resize_stream(
    load_app_env_template,  # noqa: ARG001
    map_stub,
) -> None:
    fr_output_width = int(os.getenv('FR_OUTPUT_WIDTH', '416'))
    fr_output_height = int(os.getenv('FR_OUTPUT_HEIGHT', '416'))

    # Prepare gRPC Server stub that execute process of UDF and return Response.
    generator_response = None
    try:
        generator_response = map_stub.MapFn(request_iterator=request_generator(count=1, session=1))
    except grpc.RpcError as e:
        logging.exception(e)

    # First response from stub is assumed as handshake.
    # assert that handshake response is received.
    handshake = next(generator_response)
    assert handshake.handshake.sot

    data_resp = []
    for r in generator_response:
        data_resp.append(r)

    # response + EOT Response
    assert len(data_resp) == 2

    # check vertex response
    idx = 0
    while idx < len(data_resp) - 1:
        assert len(data_resp[idx].results) == 1

        payload = msgspec.msgpack.decode(data_resp[idx].results[0].value, type=Payload)
        value = np.frombuffer(payload.compressed_frame, np.uint8)
        img = cv2.imdecode(value, cv2.IMREAD_UNCHANGED)

        # check attributes
        assert payload.frame_index == idx
        assert payload.frame_height >= fr_output_height
        assert payload.frame_width >= fr_output_width

        # check resized image
        assert img is not None
        height, width, _ = img.shape
        assert height == fr_output_height
        assert width == fr_output_width

        # capture the output from the SinkFn generator and assert.
        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
