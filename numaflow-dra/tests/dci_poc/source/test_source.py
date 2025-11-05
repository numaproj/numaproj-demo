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
from tests.dci_poc.source.utils import (
    request_generator,
)

from lib.vertex_key_io import (
    VertexKeyIO,
)

logger = setup_logging(__name__)


def test_source_under_file_src(
    source_stub,
) -> None:
    load_dotenv(str(Path(__file__).parent / '../../app.env'))
    input_type = os.getenv('SOURCE_INPUT_TYPE')
    assert input_type == 'file'

    generator_response = None
    try:
        generator_response = source_stub.ReadFn(request_generator(count=1, session=1))
    except grpc.RpcError as e:
        logging.exception(e)

    # assert that handshake response is received.
    handshake = next(generator_response)
    assert handshake.handshake.sot is True

    data_resp = []
    for r in generator_response:
        data_resp.append(r)

    # response + EOT
    assert len(data_resp) == 2

    # check vertex response
    idx = 0
    while idx < len(data_resp) - 1:
        # check payload using keys
        keys = VertexKeyIO(data_resp[idx].result.keys)
        payload = np.frombuffer(data_resp[idx].result.payload, np.uint8)
        img = cv2.imdecode(payload, cv2.IMREAD_COLOR)

        assert img is not None
        height, width, _ = img.shape

        assert keys.get('frame_idx') == idx  # index
        assert keys.get('org_height') == height  # height
        assert keys.get('org_width') == width  # width

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot is True


def test_source_under_stream_src(
    setup_video_streaming,  # noqa: ARG001
    source_stub,
) -> None:
    load_dotenv(str(Path(__file__).parent / '../../app.env'))
    input_type = os.getenv('SOURCE_INPUT_TYPE')
    assert input_type == 'stream'

    generator_response = None
    try:
        generator_response = source_stub.ReadFn(request_generator(count=1, session=1))
    except grpc.RpcError as e:
        logging.exception(e)

    # assert that handshake response is received.
    handshake = next(generator_response)
    assert handshake.handshake.sot is True

    data_resp = []
    for r in generator_response:
        data_resp.append(r)

    # response + EOT
    assert len(data_resp) == 2

    # check vertex response
    idx = 0
    while idx < len(data_resp) - 1:
        # check payload using keys
        keys = VertexKeyIO(data_resp[idx].result.keys)
        payload = np.frombuffer(data_resp[idx].result.payload, np.uint8)
        img = cv2.imdecode(payload, cv2.IMREAD_COLOR)

        assert img is not None
        height, width, _ = img.shape

        assert keys.get('frame_idx') == idx  # index
        assert keys.get('org_height') == height  # height
        assert keys.get('org_width') == width  # width

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot is True


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
