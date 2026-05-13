import logging
import sys
from datetime import UTC, datetime

import msgspec
import pytest
from pynumaflow import setup_logging
from pynumaflow._constants import STREAM_EOF
from pynumaflow.accumulator import Datum
from pynumaflow.shared.asynciter import NonBlockingIterator

from dci_poc.vertex.reduce import StreamJoiner
from lib.message_spec import BoundingBox, Payload

logger = setup_logging(__name__)


@pytest.mark.asyncio
async def test_reduce_join(
    load_app_env_template,  # noqa: ARG001
) -> None:
    stream_joiner = StreamJoiner()
    input_queue = NonBlockingIterator()
    output_queue = NonBlockingIterator()

    watermark = datetime.now(tz=UTC)

    # A frame from source
    payload_source = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source),
            event_time=datetime.now(tz=UTC),
            watermark=watermark,
            id_='source',
        )
    )

    # A result from inference
    payload_inference = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference),
            event_time=datetime.now(tz=UTC),
            watermark=watermark,
            id_='inference',
        )
    )

    await input_queue.put(STREAM_EOF)
    await stream_joiner.handler(input_queue.read_iterator(), output_queue)

    # There is one output
    await output_queue.put(STREAM_EOF)
    output_aiter = output_queue.read_iterator()
    output_item = await anext(output_aiter)

    # Metadata is merged
    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == 1
    assert payload_out.original_height == 2160
    assert payload_out.original_width == 3840
    assert len(payload_out.bounding_boxes) == 1
    assert payload_out.bounding_boxes[0].confidence == 0.9
    assert payload_out.bounding_boxes[0].class_id == 1
    assert payload_out.bounding_boxes[0].top_left_x == 0.1
    assert payload_out.bounding_boxes[0].top_left_y == 0.2
    assert payload_out.bounding_boxes[0].bottom_right_x == 0.3
    assert payload_out.bounding_boxes[0].bottom_right_y == 0.4

    # Value is a frame
    assert payload_out.compressed_frame == b'frame'

    with pytest.raises(StopAsyncIteration) as _:
        await anext(output_aiter)


@pytest.mark.asyncio
async def test_reduce_keep_frames(
    load_app_env_template,  # noqa: ARG001
) -> None:
    stream_joiner = StreamJoiner()
    input_queue = NonBlockingIterator()
    output_queue = NonBlockingIterator()

    watermark1 = datetime.now(tz=UTC)

    # First frame from source
    payload_source1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame1',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='source1',
        )
    )

    # Second frame from source
    watermark2 = datetime.now(tz=UTC)
    payload_source2 = Payload(
        frame_index=2,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame2',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source2),
            event_time=datetime.now(tz=UTC),
            watermark=watermark2,
            id_='source2',
        )
    )

    # First result from inference
    payload_inference1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='inference1',
        )
    )

    await input_queue.put(STREAM_EOF)
    await stream_joiner.handler(input_queue.read_iterator(), output_queue)

    # There is one output_queue
    await output_queue.put(STREAM_EOF)
    output_aiter = output_queue.read_iterator()
    output_item = await anext(output_aiter)

    # Metadata is merged
    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == 1
    assert payload_out.original_height == 2160
    assert payload_out.original_width == 3840
    assert len(payload_out.bounding_boxes) == 1
    assert payload_out.bounding_boxes[0].confidence == 0.9
    assert payload_out.bounding_boxes[0].class_id == 1
    assert payload_out.bounding_boxes[0].top_left_x == 0.1
    assert payload_out.bounding_boxes[0].top_left_y == 0.2
    assert payload_out.bounding_boxes[0].bottom_right_x == 0.3
    assert payload_out.bounding_boxes[0].bottom_right_y == 0.4

    # Value is a frame
    assert payload_out.compressed_frame == b'frame1'

    with pytest.raises(StopAsyncIteration) as _:
        await anext(output_aiter)


@pytest.mark.asyncio
async def test_reduce_remove_frames(
    load_app_env_template,  # noqa: ARG001
) -> None:
    stream_joiner = StreamJoiner()
    input_queue = NonBlockingIterator()
    output_queue = NonBlockingIterator()

    watermark1 = datetime.now(tz=UTC)

    # First frame from source
    payload_source1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame1',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='source1',
        )
    )

    # Second result from inference
    watermark2 = datetime.now(tz=UTC)
    payload_inference2 = Payload(
        frame_index=2,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference2),
            event_time=datetime.now(tz=UTC),
            watermark=watermark2,
            id_='inference2',
        )
    )

    # First result from inference
    # (Never be assumued in real, for test only)
    payload_inference1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='inference1',
        )
    )

    await input_queue.put(STREAM_EOF)
    await stream_joiner.handler(input_queue.read_iterator(), output_queue)

    # There is no output
    await output_queue.put(STREAM_EOF)
    with pytest.raises(StopAsyncIteration) as _:
        await anext(output_queue.read_iterator())


@pytest.mark.asyncio
async def test_reduce_keep_results(
    load_app_env_template,  # noqa: ARG001
) -> None:
    stream_joiner = StreamJoiner()
    input_queue = NonBlockingIterator()
    output_queue = NonBlockingIterator()

    watermark1 = datetime.now(tz=UTC)

    # First result from inference
    payload_inference1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='inference1',
        )
    )

    # Second result from inference
    watermark2 = datetime.now(tz=UTC)
    payload_inference2 = Payload(
        frame_index=2,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.5,
                top_left_y=0.6,
                bottom_right_x=0.7,
                bottom_right_y=0.8,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference2),
            event_time=datetime.now(tz=UTC),
            watermark=watermark2,
            id_='inference2',
        )
    )

    # First frame from source
    payload_source1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame1',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='source1',
        )
    )

    await input_queue.put(STREAM_EOF)
    await stream_joiner.handler(input_queue.read_iterator(), output_queue)

    # There is one output_queue
    await output_queue.put(STREAM_EOF)
    output_aiter = output_queue.read_iterator()
    output_item = await anext(output_aiter)

    # Keys are merged
    payload_out = msgspec.msgpack.decode(output_item.value, type=Payload)
    assert payload_out.frame_index == 1
    assert payload_out.original_height == 2160
    assert payload_out.original_width == 3840
    assert len(payload_out.bounding_boxes) == 1
    assert payload_out.bounding_boxes[0].confidence == 0.9
    assert payload_out.bounding_boxes[0].class_id == 1
    assert payload_out.bounding_boxes[0].top_left_x == 0.1
    assert payload_out.bounding_boxes[0].top_left_y == 0.2
    assert payload_out.bounding_boxes[0].bottom_right_x == 0.3
    assert payload_out.bounding_boxes[0].bottom_right_y == 0.4

    # Value is a frame
    assert payload_out.compressed_frame == b'frame1'

    with pytest.raises(StopAsyncIteration) as _:
        await anext(output_aiter)


@pytest.mark.asyncio
async def test_reduce_remove_results(
    load_app_env_template,  # noqa: ARG001
) -> None:
    stream_joiner = StreamJoiner()
    input_queue = NonBlockingIterator()
    output_queue = NonBlockingIterator()

    watermark1 = datetime.now(tz=UTC)

    # First result from inference
    payload_inference1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        bounding_boxes=[
            BoundingBox(
                confidence=0.9,
                class_id=1,
                top_left_x=0.1,
                top_left_y=0.2,
                bottom_right_x=0.3,
                bottom_right_y=0.4,
            )
        ],
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_inference1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='inference1',
        )
    )

    # Second frame from source
    watermark2 = datetime.now(tz=UTC)
    payload_source2 = Payload(
        frame_index=2,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame2',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source2),
            event_time=datetime.now(tz=UTC),
            watermark=watermark2,
            id_='source2',
        )
    )

    # First frame from source
    # (Never be assumued in real, for test only)
    payload_source1 = Payload(
        frame_index=1,
        original_height=2160,
        original_width=3840,
        compressed_frame=b'frame1',
    )
    await input_queue.put(
        Datum(
            keys=['NON_KEYED_STREAM'],
            value=msgspec.msgpack.encode(payload_source1),
            event_time=datetime.now(tz=UTC),
            watermark=watermark1,
            id_='source1',
        )
    )

    await input_queue.put(STREAM_EOF)
    await stream_joiner.handler(input_queue.read_iterator(), output_queue)

    # There is no output
    await output_queue.put(STREAM_EOF)
    with pytest.raises(StopAsyncIteration) as _:
        await anext(output_queue.read_iterator())


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(['-qq'], plugins=[]))
