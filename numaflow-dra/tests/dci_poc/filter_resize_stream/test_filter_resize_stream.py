import logging
import os
import sys
from pathlib import Path

import cv2
import grpc
import numpy as np
import pytest
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import MapStreamAsyncServer
from pynumaflow.mapstreamer.servicer.async_servicer import AsyncMapStreamServicer
from tests.dci_poc.filter_resize_stream.utils import request_generator

from dci_poc.vertex.filter_resize_stream import FilterResize
from lib.vertex_key_io import (
    VertexKeyIO,
)

logger = setup_logging(__name__)


@pytest.fixture
def map_servicer_impl() -> AsyncMapStreamServicer:
    handler = FilterResize()
    server = MapStreamAsyncServer(handler)
    udf = server.servicer
    return udf


def test_filter_resize_stream(map_stub) -> None:
    # setup ENV
    load_dotenv(str(Path(__file__).parent / '../../../../app.env'))
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

        keys = VertexKeyIO(data_resp[idx].results[0].keys)
        value = np.frombuffer(data_resp[idx].results[0].value, np.uint8)
        img = cv2.imdecode(value, cv2.IMREAD_UNCHANGED)

        # check attributes
        assert keys.get('frame_idx') == idx
        assert keys.get('org_height') >= fr_output_height
        assert keys.get('org_width') >= fr_output_width

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
