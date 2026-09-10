import logging
import os
import sys
from datetime import UTC, datetime

import msgspec
import pytest
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import Datum
from tests.testing_utils import compress_frame, decompress_frame, mock_4k_frame, mock_hd_frame

from dci_poc.vertex_gpu_fr.filter_resize_stream import FilterResize
from lib.message_spec import Payload

logger = setup_logging(__name__)


# Source -> **FR** -> Inference
@pytest.mark.asyncio
async def test_filter_resize_stream_handler() -> None:
    os.environ['FR_OUTPUT_HEIGHT'] = '416'
    os.environ['FR_OUTPUT_WIDTH'] = '416'

    filter_resize = FilterResize()

    frame_index = 0
    keys = [str(frame_index)]
    frame = mock_4k_frame()
    compressed_frame = compress_frame(frame)

    # A frame from source
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

    output_item = await anext(filter_resize.handler(keys, datum))

    assert output_item.keys == keys

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert payload_out.frame_width == int(os.getenv('FR_OUTPUT_WIDTH'))
    assert payload_out.bounding_boxes == []
    assert payload_out.compressed_frame is not None
    assert payload_out.compressed_frame != compressed_frame

    output_frame = decompress_frame(payload_out.compressed_frame)
    assert output_frame.shape[0] == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert output_frame.shape[1] == int(os.getenv('FR_OUTPUT_WIDTH'))

    assert payload_out.secondary_frame is None


# Source -> **FR** -> Reduce
@pytest.mark.asyncio
async def test_filter_resize_stream_handler_bypass() -> None:
    os.environ['FR_OUTPUT_HEIGHT'] = '1080'
    os.environ['FR_OUTPUT_WIDTH'] = '1920'

    filter_resize = FilterResize()

    frame_index = 1
    keys = [str(frame_index)]
    frame = mock_4k_frame()
    compressed_frame = compress_frame(frame)

    # A frame from source
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

    output_item = await anext(filter_resize.handler(keys, datum))

    assert output_item.keys == keys

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert payload_out.frame_width == int(os.getenv('FR_OUTPUT_WIDTH'))
    assert payload_out.bounding_boxes == []
    assert payload_out.compressed_frame is not None
    assert payload_out.compressed_frame != compressed_frame

    output_frame = decompress_frame(payload_out.compressed_frame)
    assert output_frame.shape[0] == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert output_frame.shape[1] == int(os.getenv('FR_OUTPUT_WIDTH'))

    assert payload_out.secondary_frame is None


# Source -> **FR(1st)** -> FR(2nd) -> Inference
@pytest.mark.asyncio
async def test_filter_resize_stream_handler_first_stage() -> None:
    os.environ['FR_OUTPUT_WIDTH'] = '1920'
    os.environ['FR_OUTPUT_HEIGHT'] = '1080'
    os.environ['KEEP_SECONDARY_FRAME'] = '1'

    filter_resize = FilterResize()

    frame_index = 2
    keys = [str(frame_index)]
    frame = mock_4k_frame()
    compressed_frame = compress_frame(frame)

    # A frame from source
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

    output_item = await anext(filter_resize.handler(keys, datum))

    assert output_item.keys == keys

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert payload_out.frame_width == int(os.getenv('FR_OUTPUT_WIDTH'))
    assert payload_out.bounding_boxes == []
    assert payload_out.compressed_frame is not None
    assert payload_out.compressed_frame != compressed_frame

    output_frame = decompress_frame(payload_out.compressed_frame)
    assert output_frame.shape[0] == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert output_frame.shape[1] == int(os.getenv('FR_OUTPUT_WIDTH'))

    # Keep an input frame as an ouput secondary frame if KEEP_SECONDARY_FRAME=1
    assert payload_out.secondary_frame is not None
    assert payload_out.secondary_frame == compressed_frame


# Source -> FR(1st) -> **FR(2nd)** -> Inference
@pytest.mark.asyncio
async def test_filter_resize_stream_handler_second_stage() -> None:
    os.environ['FR_OUTPUT_WIDTH'] = '416'
    os.environ['FR_OUTPUT_HEIGHT'] = '416'
    os.environ['KEEP_SECONDARY_FRAME'] = '1'

    filter_resize = FilterResize()

    frame_index = 3
    keys = [str(frame_index)]
    frame = mock_hd_frame()
    compressed_frame = compress_frame(frame)

    # A frame from another filter resize
    payload_in = Payload(
        frame_index=frame_index,
        frame_height=frame.shape[0],
        frame_width=frame.shape[1],
        compressed_frame=compressed_frame,
        secondary_frame=b'secondary_frame_being_dropped',
    )
    datum = Datum(
        keys=keys,
        value=msgspec.msgpack.encode(payload_in),
        event_time=datetime.now(tz=UTC),
        watermark=datetime.now(tz=UTC),
    )

    output_item = await anext(filter_resize.handler(keys, datum))

    assert output_item.keys == keys

    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == frame_index
    assert payload_out.frame_height == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert payload_out.frame_width == int(os.getenv('FR_OUTPUT_WIDTH'))
    assert payload_out.bounding_boxes == []
    assert payload_out.compressed_frame is not None
    assert payload_out.compressed_frame != compressed_frame
    assert payload_out.secondary_frame is not None

    output_frame = decompress_frame(payload_out.compressed_frame)
    assert output_frame.shape[0] == int(os.getenv('FR_OUTPUT_HEIGHT'))
    assert output_frame.shape[1] == int(os.getenv('FR_OUTPUT_WIDTH'))

    # Keep an input frame as an ouput secondary frame if KEEP_SECONDARY_FRAME=1
    assert payload_out.secondary_frame is not None
    assert payload_out.secondary_frame == compressed_frame


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
