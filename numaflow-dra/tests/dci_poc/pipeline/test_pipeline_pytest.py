import os
from datetime import datetime
from pathlib import Path

import cv2
import pytest
from pynumaflow._constants import DROP, STREAM_EOF
from pynumaflow.mapstreamer import Datum as MapDatum
from pynumaflow.shared.asynciter import NonBlockingIterator
from pynumaflow.sinker import Datum as SinkDatum
from pynumaflow.sourcer import (
    AckRequest,
    ReadRequest,
)
from tests.testing_utils import mock_4k_frame

from dci_poc.vertex.filter_resize_stream import FilterResize
from dci_poc.vertex.sink import AsyncSink
from dci_poc.vertex.source import AsyncSourceSendFrame
from dci_poc.vertex_gpu_yolov4.inference_stream_yolov4 import Infer
from lib.vertex_key_io import VertexKeyIO


async def input_from_source(source):
    source_output = NonBlockingIterator()
    await source.read_handler(ReadRequest(num_records=1, timeout_in_ms=1000), source_output)
    return await anext(source_output.read_iterator())


async def apply_map(mapper, message, headers):
    input_datum = MapDatum(
        message.keys,
        message.payload if hasattr(message, 'payload') else message.value,
        datetime.now(),  # Do not care
        datetime.now(),  # Do not care
        headers,
    )
    output_message = mapper.handler([], input_datum)
    return await anext(aiter(output_message))


async def output_to_sink(udsink, message, headers, message_id):
    sink_datums = NonBlockingIterator()
    await sink_datums.put(
        SinkDatum(
            message.keys,
            message_id,
            message.value,
            datetime.now(),  # Do not care
            datetime.now(),  # Do not care
            headers,
        ),
    )
    await sink_datums.put(STREAM_EOF)
    return await udsink.handler(sink_datums.read_iterator())


# Provides a mock read function which returns mock frames for test_frame_index
class ReadTwoMockedFrames:
    NUM_MAX_FRAMES = 2

    def __init__(self):
        self.num_frames = 0

    def read(self):
        # The first and second frame
        if self.num_frames < self.NUM_MAX_FRAMES:
            self.num_frames += 1
            # Return a mocked frame from which no inference result will be got
            return True, mock_4k_frame()

        # There is no third frame
        return False, None


# Provides a mock read function which returns a real frame (read from file)
# for test_data_structure
class ReadOneRealFrame:
    NUM_MAX_FRAMES = 1
    EXPECTED_SHAPE = (2160, 3840, 3)

    def __init__(self):
        self.num_frames = 0

    def read(self):
        # The first frame
        if self.num_frames == 0:
            frame = cv2.imread(str(Path(__file__).parent / '../../../0001.png'))
            if frame is None:
                raise Exception
            # Abort if the shape of the input frame is not equal to
            # the expected one
            if frame.shape != self.EXPECTED_SHAPE:
                raise Exception
            self.num_frames += 1
            return True, frame

        # There is no second frame
        return False, None


@pytest.fixture
def mock_cv2_video_capture(mocker):
    cv2_video_capture = mocker.patch('cv2.VideoCapture')
    # Have cap.isOpened() in the source return True,
    # where cap = cv2.VideoCapture(src_path)
    cap = cv2_video_capture.return_value
    cap.isOpened.return_value = True

    return cv2_video_capture


@pytest.fixture
def mock_cv2_video_capture_mocked_frames(mock_cv2_video_capture):
    # Have cap.get(cv2.CAP_PROP_FRAME_COUNT) and cap.read() return
    # 2 mocked frames, where cap = cv2.Videocapture(src_path)
    cap = mock_cv2_video_capture.return_value
    cap.get.return_value = ReadTwoMockedFrames.NUM_MAX_FRAMES
    cap.read.side_effect = ReadTwoMockedFrames().read

    return mock_cv2_video_capture


@pytest.fixture
def mock_cv2_video_capture_real_frame(mock_cv2_video_capture):
    # Have cap.get(cv2.CAP_PROP_FRAME_COUNT) and cap.read() return
    # 1 real frame, where cap = cv2.Videocapture(src_path)
    cap = mock_cv2_video_capture.return_value
    cap.get.return_value = ReadOneRealFrame.NUM_MAX_FRAMES
    cap.read.side_effect = ReadOneRealFrame().read

    return mock_cv2_video_capture


# Test that frames are processed in order without being dropped
@pytest.mark.asyncio
async def test_frame_index(mock_cv2_video_capture_mocked_frames):
    # Assert that the mock functions are not called yet
    mock_cv2_video_capture_mocked_frames.assert_not_called()
    mock_cv2_video_capture_mocked_frames.return_value.isOpened.assert_not_called()
    mock_cv2_video_capture_mocked_frames.return_value.get.assert_not_called()
    mock_cv2_video_capture_mocked_frames.return_value.read.assert_not_called()

    # Make a pipeline except sink which will not be called
    filter_resize = FilterResize()
    inference = Infer()
    # Initialize last due to the relationship between initialization and frame emission
    udsource = AsyncSourceSendFrame()

    ######################################################################
    # Send the first and second frames to the pipeline
    ######################################################################
    for i in range(mock_cv2_video_capture_mocked_frames.return_value.get()):
        source_message = await input_from_source(udsource)
        mock_cv2_video_capture_mocked_frames.return_value.read.assert_called()

        vk_io_source = VertexKeyIO(source_message.keys)
        assert vk_io_source['frame_idx'] == i

        await udsource.ack_handler(AckRequest([source_message.offset]))

        filter_resize_message = await apply_map(
            filter_resize,
            source_message,
            source_message.headers,
        )

        vk_io_filter_resize = VertexKeyIO(filter_resize_message.keys)
        assert vk_io_filter_resize['frame_idx'] == i

        inference_message = await apply_map(
            inference,
            filter_resize_message,
            source_message.headers,
        )

        # Using a mock frame for the input data,
        # Each frame should be dropped
        assert len(inference_message.tags) == 1
        assert inference_message.tags[0] == DROP

    ######################################################################
    # Send the third frame, but don't send any more after that
    ######################################################################
    with pytest.raises(StopAsyncIteration):
        await input_from_source(udsource)


@pytest.mark.asyncio
async def test_data_structure(mock_cv2_video_capture_real_frame):
    # Assert that the mock functions are not called yet
    mock_cv2_video_capture_real_frame.assert_not_called()
    mock_cv2_video_capture_real_frame.return_value.isOpened.assert_not_called()
    mock_cv2_video_capture_real_frame.return_value.get.assert_not_called()
    mock_cv2_video_capture_real_frame.return_value.read.assert_not_called()

    # Make a pipeline
    udsource = AsyncSourceSendFrame()
    filter_resize = FilterResize()
    inference = Infer()
    udsink = AsyncSink()

    ######################################################################
    # Send the first frame
    ######################################################################
    source_message = await input_from_source(udsource)
    mock_cv2_video_capture_real_frame.return_value.read.assert_called()

    assert type(source_message.payload) is bytes
    assert source_message.offset.offset == b'0'
    assert source_message.offset.partition_id == int(os.getenv('NUMAFLOW_REPLICA', '0'))
    assert type(source_message.event_time) is datetime
    vk_io_source = VertexKeyIO(source_message.keys)
    assert len(vk_io_source) == 3
    assert vk_io_source['frame_idx'] == 0
    assert vk_io_source['org_height'] == 2160
    assert vk_io_source['org_width'] == 3840
    assert type(source_message.headers['x-txn-id']) is str

    await udsource.ack_handler(AckRequest([source_message.offset]))

    filter_resize_message = await apply_map(filter_resize, source_message, source_message.headers)

    assert type(filter_resize_message.value) is bytes
    vk_io_filter_resize = VertexKeyIO(filter_resize_message.keys)
    assert len(vk_io_filter_resize) == 3
    assert vk_io_filter_resize['frame_idx'] == 0
    assert vk_io_filter_resize['org_height'] == 2160
    assert vk_io_filter_resize['org_width'] == 3840

    inference_message = await apply_map(inference, filter_resize_message, source_message.headers)

    assert type(inference_message.value) is bytes
    vk_io_inference = VertexKeyIO(inference_message.keys)
    assert len(vk_io_inference) == 10
    assert vk_io_inference['frame_idx'] == 0
    assert vk_io_inference['org_height'] == 2160
    assert vk_io_inference['org_width'] == 3840

    sink_output = await output_to_sink(udsink, inference_message, source_message.headers, 'foo')

    assert len(sink_output) == 1
    assert sink_output[0].id == 'foo'
    assert sink_output[0].success

    ######################################################################
    # Send the second frame, but don't send any more after that
    ######################################################################
    with pytest.raises(StopAsyncIteration):
        await input_from_source(udsource)
