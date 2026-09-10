import msgspec
from pynumaflow.proto.mapper import map_pb2
from tests.testing_utils import compress_frame, get_time_args, mock_4k_frame, mock_headers

from lib.message_spec import Payload


def request_generator(count, session=1, handshake=True):
    event_time_timestamp, watermark_timestamp = get_time_args()

    read_idx = 0

    if handshake:
        yield map_pb2.MapRequest(handshake=map_pb2.Handshake(sot=True))

    for _j in range(session):
        for i in range(count):
            frame = mock_4k_frame()

            payload = Payload(
                frame_index=read_idx,
                frame_height=frame.shape[0],
                frame_width=frame.shape[1],
                compressed_frame=compress_frame(frame),
            )

            req = map_pb2.MapRequest(
                request=map_pb2.MapRequest.Request(
                    value=msgspec.msgpack.encode(payload),
                    event_time=event_time_timestamp,
                    watermark=watermark_timestamp,
                    headers=mock_headers(),
                ),
                id='test-id-' + str(i),
            )
            read_idx += 1
            yield req
