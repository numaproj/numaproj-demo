import cv2
import msgspec
import numpy as np
from pynumaflow.proto.mapper import map_pb2
from tests.testing_utils import get_time_args

from lib.message_spec import Payload


def request_generator(count, session=1, handshake=True):
    event_time_timestamp, watermark_timestamp = get_time_args()

    read_idx = 0

    if handshake:
        yield map_pb2.MapRequest(handshake=map_pb2.Handshake(sot=True))

    for _j in range(session):
        for i in range(count):
            with open(
                '../../ml-models/official-yolov7/deploy/triton-inference-server/data/dog.jpg', 'rb'
            ) as f:
                encoded_frame = f.read()
            frame = cv2.imdecode(np.frombuffer(encoded_frame, np.uint8), cv2.IMREAD_UNCHANGED)
            payload = Payload(
                frame_index=read_idx,
                original_height=frame.shape[0],
                original_width=frame.shape[1],
                compressed_frame=encoded_frame,
            )

            req = map_pb2.MapRequest(
                request=map_pb2.MapRequest.Request(
                    value=msgspec.msgpack.encode(payload),
                    event_time=event_time_timestamp,
                    watermark=watermark_timestamp,
                ),
                id='test-id-' + str(i),
            )
            read_idx += 1
            yield req
