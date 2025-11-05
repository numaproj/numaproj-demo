import cv2
import numpy as np
from pynumaflow.proto.mapper import map_pb2
from tests.testing_utils import get_time_args

from lib.vertex_key_io import VertexKeyIO


def request_generator(count, session=1, handshake=True):
    event_time_timestamp, watermark_timestamp = get_time_args()

    read_idx = 0

    if handshake:
        yield map_pb2.MapRequest(handshake=map_pb2.Handshake(sot=True))

    for _j in range(session):
        for i in range(count):
            with open('../../ml-models/pytorch-YOLOv4/data/dog.jpg', 'rb') as f:
                encoded_frame = f.read()
            frame = cv2.imdecode(np.frombuffer(encoded_frame, np.uint8), cv2.IMREAD_UNCHANGED)
            vk_io = VertexKeyIO()
            vk_io.add('frame_idx', read_idx)
            vk_io.add('org_height', frame.shape[0])
            vk_io.add('org_width', frame.shape[1])

            req = map_pb2.MapRequest(
                request=map_pb2.MapRequest.Request(
                    value=encoded_frame,
                    event_time=event_time_timestamp,
                    watermark=watermark_timestamp,
                    keys=vk_io.keys_list,
                ),
                id='test-id-' + str(i),
            )
            read_idx += 1
            yield req
