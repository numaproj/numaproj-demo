import logging
import os
import sys
from datetime import UTC, datetime

import msgspec
import pytest
from pynumaflow import setup_logging
from pynumaflow._constants import DROP
from pynumaflow.mapstreamer import Datum
from tests.testing_utils import compress_frame, mock_416_frame, mock_hd_frame

from dci_poc.vertex_gpu_yolov7.inference_stream_yolov7 import Infer
from lib.message_spec import Payload

logger = setup_logging(__name__)


# FR -> **Inference** -> Reduce -> Sink
@pytest.mark.asyncio
async def test_inference_stream_yolov7_handler_with_reduce() -> None:
    inference = Infer()

    frame_index = 0
    keys = [str(frame_index)]
    frame = mock_416_frame()
    compressed_frame = compress_frame(frame)

    # A frame from filter resize
    payload_in = Payload(
        frame_index=frame_index,
        frame_height=frame.shape[0],
        frame_width=frame.shape[1],
        compressed_frame=compressed_frame,
    )
    datum = Datum(
        keys=keys,
        value=msgspec.msgpack.encode(payload_in),
        event_time=datetime.now(tz=UTC),
        watermark=datetime.now(tz=UTC),
    )

    output_item = await anext(inference.handler(keys, datum))

    # Nothing will be detected from a mocked frame but
    # no output message will be dropped
    assert output_item.keys == keys
    assert output_item.value is not None
    assert output_item.value != b''
    assert output_item.tags != [DROP]

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height is None
    assert payload_out.frame_width is None
    assert payload_out.bounding_boxes == []
    assert payload_out.compressed_frame is None
    assert payload_out.secondary_frame is None


# FR -> **Inference** -> Sink
@pytest.mark.asyncio
async def test_inference_stream_yolov7_handler_map_only() -> None:
    os.environ['KEEP_SECONDARY_FRAME'] = '1'

    inference = Infer()

    frame_index = 1
    keys = [str(frame_index)]
    frame = mock_416_frame()
    compressed_frame = compress_frame(frame)

    frame_hd = mock_hd_frame()
    secondary_frame = compress_frame(frame_hd)

    # A frame from source
    payload_in = Payload(
        frame_index=frame_index,
        frame_height=frame.shape[0],
        frame_width=frame.shape[1],
        compressed_frame=compressed_frame,
        secondary_frame=secondary_frame,
    )
    datum = Datum(
        keys=keys,
        value=msgspec.msgpack.encode(payload_in),
        event_time=datetime.now(tz=UTC),
        watermark=datetime.now(tz=UTC),
    )

    output_item = await anext(inference.handler(keys, datum))

    assert output_item.keys == keys

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height is None
    assert payload_out.frame_width is None
    assert payload_out.bounding_boxes == []

    # Keep an input secondary frame as an output compressed frame
    assert payload_out.compressed_frame is not None
    assert payload_out.compressed_frame == secondary_frame
    assert payload_out.secondary_frame is None


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
