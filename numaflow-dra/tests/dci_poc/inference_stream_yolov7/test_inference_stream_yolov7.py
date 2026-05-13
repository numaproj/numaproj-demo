import logging
import sys

import grpc
import msgspec
import pytest
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import MapStreamAsyncServer
from pynumaflow.proto.mapper import map_pb2_grpc
from tests.dci_poc.inference_stream_yolov7.utils import request_generator

from dci_poc.vertex_gpu_yolov7.inference_stream_yolov7 import Infer
from lib.message_spec import Payload

logger = setup_logging(__name__)


@pytest.fixture
def map_servicer_impl() -> map_pb2_grpc.MapServicer:
    handler = Infer()
    server = MapStreamAsyncServer(handler)
    udf = server.servicer
    return udf


def test_inference_stream(
    load_app_env_template,  # noqa: ARG001
    map_stub,
) -> None:
    generator_response = None
    try:
        generator_response = map_stub.MapFn(request_iterator=request_generator(count=1, session=1))
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

        payload = msgspec.msgpack.decode(data_resp[idx].results[0].value, type=Payload)
        assert payload.compressed_frame is None

        assert payload.frame_index == idx
        # Depends on the input data.
        # If it is a photo of a dog and a bicycle in the COCO dataset:
        assert len(payload.bounding_boxes) == 4

        assert payload.bounding_boxes[0].class_id == 'bicycle'
        assert payload.bounding_boxes[0].confidence > 0.0
        assert payload.bounding_boxes[0].top_left_x > 0.0
        assert payload.bounding_boxes[0].top_left_y > 0.0
        assert payload.bounding_boxes[0].bottom_right_x > 0.0
        assert payload.bounding_boxes[0].bottom_right_y > 0.0

        assert payload.bounding_boxes[1].class_id == 'dog'
        assert payload.bounding_boxes[1].confidence > 0.0
        assert payload.bounding_boxes[1].top_left_x > 0.0
        assert payload.bounding_boxes[1].top_left_y > 0.0
        assert payload.bounding_boxes[1].bottom_right_x > 0.0
        assert payload.bounding_boxes[1].bottom_right_y > 0.0

        assert payload.bounding_boxes[2].class_id == 'truck'
        assert payload.bounding_boxes[2].confidence > 0.0
        assert payload.bounding_boxes[2].top_left_x > 0.0
        assert payload.bounding_boxes[2].top_left_y > 0.0
        assert payload.bounding_boxes[2].bottom_right_x > 0.0
        assert payload.bounding_boxes[2].bottom_right_y > 0.0

        assert payload.bounding_boxes[3].class_id == 'car'
        assert payload.bounding_boxes[3].confidence > 0.0
        assert payload.bounding_boxes[3].top_left_x > 0.0
        assert payload.bounding_boxes[3].top_left_y > 0.0
        assert payload.bounding_boxes[3].bottom_right_x > 0.0
        assert payload.bounding_boxes[3].bottom_right_y > 0.0

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
