import os

import cv2
import msgspec
from pynumaflow.proto.sinker import sink_pb2
from tests.testing_utils import get_time_args, mock_4k_frame

from lib.message_spec import BoundingBox, Payload


def request_generator(count, session=1, handshake=True):
    event_time_timestamp, watermark_timestamp = get_time_args()

    read_idx = 0

    if handshake:
        yield sink_pb2.SinkRequest(handshake=sink_pb2.Handshake(sot=True))

    for _j in range(session):
        for i in range(count):
            fr_output_width = int(os.getenv('FR_OUTPUT_WIDTH', '416'))
            fr_output_height = int(os.getenv('FR_OUTPUT_HEIGHT', '416'))
            jpeg_quality = int(os.getenv('JPEG_QUALITY', '90'))
            frame = mock_4k_frame()
            resized_frame = cv2.resize(frame, (fr_output_width, fr_output_height))
            _, buf = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            payload = Payload(
                frame_index=read_idx,
                bounding_boxes=[
                    BoundingBox(
                        confidence=0.9,
                        class_id=1,
                        top_left_x=0.3,
                        top_left_y=0.3,
                        bottom_right_x=0.7,
                        bottom_right_y=0.7,
                    )
                ],
                compressed_frame=buf.tobytes(),
            )

            req = sink_pb2.SinkRequest(
                request=sink_pb2.SinkRequest.Request(
                    id='test-id-' + str(i),
                    event_time=event_time_timestamp,
                    watermark=watermark_timestamp,
                    value=msgspec.msgpack.encode(payload),
                ),
            )
            read_idx += 1
            yield req

        yield sink_pb2.SinkRequest(status=sink_pb2.TransmissionStatus(eot=True))
