import logging
import os
import sys

import cv2
import grpc
import msgspec
import numpy as np
import pytest
from pynumaflow import setup_logging
from tests.dci_poc.source.utils import (
    request_generator,
)

from lib.message_spec import Payload

logger = setup_logging(__name__)


def test_source_under_file_src(
    load_app_env_template,  # noqa: ARG001
    source_stub,
) -> None:
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
        # check payload
        payload = msgspec.msgpack.decode(data_resp[idx].result.payload, type=Payload)
        compressed_frame = np.frombuffer(payload.compressed_frame, np.uint8)
        img = cv2.imdecode(compressed_frame, cv2.IMREAD_COLOR)

        assert img is not None
        height, width, _ = img.shape

        assert payload.frame_index == idx
        assert payload.frame_height == height
        assert payload.frame_width == width

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot is True


def test_source_under_stream_src(
    load_app_env_template,  # noqa: ARG001
    setup_video_streaming,  # noqa: ARG001
    source_stub,
) -> None:
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
        # check payload
        payload = msgspec.msgpack.decode(data_resp[idx].result.payload, type=Payload)
        compressed_frame = np.frombuffer(payload.compressed_frame, np.uint8)
        img = cv2.imdecode(compressed_frame, cv2.IMREAD_COLOR)

        assert img is not None
        height, width, _ = img.shape

        assert payload.frame_index == idx
        assert payload.frame_height == height
        assert payload.frame_width == width

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot is True


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
