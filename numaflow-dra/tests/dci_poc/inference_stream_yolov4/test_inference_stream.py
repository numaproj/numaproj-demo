import logging
import pickle
import sys

import grpc
import pytest
from dotenv import load_dotenv
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import MapStreamAsyncServer
from pynumaflow.proto.mapper import map_pb2_grpc
from tests.dci_poc.inference_stream.utils import request_generator

from dci_poc.vertex_gpu.inference_stream import Infer
from lib.vertex_key_io import (
    VertexKeyIO,
)

LOGGER = setup_logging(__name__)


@pytest.fixture
def map_servicer_impl() -> map_pb2_grpc.MapServicer:
    handler = Infer()
    server = MapStreamAsyncServer(handler)
    udf = server.servicer
    return udf


def test_inference_stream(stub) -> None:
    # setup ENV
    load_dotenv('../../../../app.env')

    generator_response = None
    try:
        generator_response = stub.MapFn(request_iterator=request_generator(count=1, session=1))
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

        keys = VertexKeyIO(data_resp[idx].results[0].keys)
        value = data_resp[idx].results[0].value
        img = pickle.loads(value)

        assert keys.get('frame_idx') == idx
        assert keys.get('box_len') >= 1
        assert keys.get('box_0_confidence') > 0.0
        # Depends on the input data.
        # If the input data is a dog with class_id: 1 in the COCO dataset
        assert keys.get('box_0_class_id') == 1
        assert keys.get('box_0_LeftUpX') > 0.0
        assert keys.get('box_0_LeftUpY') > 0.0
        assert keys.get('box_0_RightDownX') > 0.0
        assert keys.get('box_0_RightDownY') > 0.0

        assert img is not None
        assert img.shape[0] == keys.get('org_height')
        assert img.shape[1] == keys.get('org_width')

        idx += 1

    # EOT Response
    assert data_resp[len(data_resp) - 1].status.eot


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
