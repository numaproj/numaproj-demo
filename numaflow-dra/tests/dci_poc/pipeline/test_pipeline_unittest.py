import os
from datetime import datetime
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import cv2
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
from dci_poc.vertex_gpu.inference_stream import Infer


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


def patch_cv2_video_capture(num_frames, read_fn):
    patcher_cv2_video_capture = patch('cv2.VideoCapture')
    mock_cv2_video_capture = patcher_cv2_video_capture.start()
    # Have cap.isOpened() in the source return True,
    # where cap = cv2.Videocapture(src_path)
    cap = mock_cv2_video_capture.return_value
    cap.isOpened.return_value = True
    # Have cap.get(cv2.CAP_PROP_FRAME_COUNT) in the source return frame(s)
    # with the given class
    cap.get.return_value = num_frames
    cap.read.side_effect = read_fn

    return (patcher_cv2_video_capture, mock_cv2_video_capture)


def patch_os_path_exists():
    patcher_os_path_exists = patch('os.path.exists')
    mock_os_path_exists = patcher_os_path_exists.start()
    # Have op.path.exists(src_path) return True
    mock_os_path_exists.return_value = True

    return (patcher_os_path_exists, mock_os_path_exists)


class TestFrameIndex(IsolatedAsyncioTestCase):
    NUM_MAX_FRAMES = 2

    def setUp(self):
        self.num_frames = 0
        # Patch functions
        (self.patcher_cv2_video_capture, self.mock_cv2_video_capture) = patch_cv2_video_capture(
            self.NUM_MAX_FRAMES,
            self.read,
        )
        (self.patcher_os_path_exists, self.mock_os_path_exists) = patch_os_path_exists()

    def tearDown(self):
        self.patcher_os_path_exists.stop()
        self.patcher_cv2_video_capture.stop()

    def read(self):
        # The first and second frame
        if self.num_frames < self.NUM_MAX_FRAMES:
            self.num_frames += 1
            # Return a mocked frame from which no inference result will be got
            return True, mock_4k_frame()

        # There is no third frame
        return False, None

    async def test_frame_index(self):
        # Assert that mock functions are not called yet
        self.mock_os_path_exists.assert_not_called()
        self.mock_cv2_video_capture.assert_not_called()
        self.mock_cv2_video_capture.return_value.isOpened.assert_not_called()
        self.mock_cv2_video_capture.return_value.get.assert_not_called()
        self.mock_cv2_video_capture.return_value.read.assert_not_called()

        # Make a pipeline except sink which will not be called
        udsource = AsyncSourceSendFrame()
        self.mock_os_path_exists.assert_called_once()
        self.mock_cv2_video_capture.assert_called_once()
        self.mock_cv2_video_capture.return_value.isOpened.assert_called_once()
        self.mock_cv2_video_capture.return_value.get.assert_called()
        filter_resize = FilterResize()
        inference = Infer()

        ######################################################################
        # Flow the first and second frames
        ######################################################################
        for i in range(self.NUM_MAX_FRAMES):
            source_message = await input_from_source(udsource)
            self.mock_cv2_video_capture.return_value.get.assert_called()

            self.assertEqual(source_message.offset.offset, str(i).encode('utf-8'))
            self.assertEqual(source_message.keys[0], str(i))

            await udsource.ack_handler(AckRequest([source_message.offset]))

            filter_resize_message = await apply_map(
                filter_resize,
                source_message,
                source_message.headers,
            )

            self.assertEqual(filter_resize_message.keys[0], str(i))

            inference_message = await apply_map(
                inference,
                filter_resize_message,
                source_message.headers,
            )

            # Each frame should be dropped
            self.assertEqual(len(inference_message.tags), 1)
            self.assertEqual(inference_message.tags[0], DROP)

        ######################################################################
        # Try to flow the third frame but no more
        ######################################################################
        with self.assertRaises(StopAsyncIteration):
            await input_from_source(udsource)


class TestDataStructure(IsolatedAsyncioTestCase):
    NUM_MAX_FRAMES = 1
    EXPECTED_SHAPE = (2160, 3840, 3)  # landspace

    def setUp(self):
        self.num_frames = 0
        # Patch functions
        (self.patcher_cv2_video_capture, self.mock_cv2_video_capture) = patch_cv2_video_capture(
            self.NUM_MAX_FRAMES,
            self.read,
        )
        (self.patcher_os_path_exists, self.mock_os_path_exists) = patch_os_path_exists()

    def tearDown(self):
        self.patcher_os_path_exists.stop()
        self.patcher_cv2_video_capture.stop()

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

    async def test_data_structure(self):
        # Assert that mock functions are not called yet
        self.mock_os_path_exists.assert_not_called()
        self.mock_cv2_video_capture.assert_not_called()
        self.mock_cv2_video_capture.return_value.isOpened.assert_not_called()
        self.mock_cv2_video_capture.return_value.get.assert_not_called()
        self.mock_cv2_video_capture.return_value.read.assert_not_called()

        # Make a pipeline
        udsource = AsyncSourceSendFrame()
        self.mock_os_path_exists.assert_called_once()
        self.mock_cv2_video_capture.assert_called_once()
        self.mock_cv2_video_capture.return_value.isOpened.assert_called_once()
        self.mock_cv2_video_capture.return_value.get.assert_called()
        filter_resize = FilterResize()
        inference = Infer()
        udsink = AsyncSink()

        ######################################################################
        # Flow the first frame
        ######################################################################
        source_message = await input_from_source(udsource)
        self.mock_cv2_video_capture.return_value.read.assert_called()

        self.assertIs(type(source_message.payload), bytes)
        self.assertEqual(source_message.offset.offset, b'0')
        self.assertIs(source_message.offset.partition_id, int(os.getenv('NUMAFLOW_REPLICA', '0')))
        self.assertIs(type(source_message.event_time), datetime)
        self.assertEqual(len(source_message.keys), 3)
        self.assertEqual(source_message.keys[0], '0')
        self.assertEqual(source_message.keys[1], '2160')
        self.assertEqual(source_message.keys[2], '3840')
        self.assertIs(type(source_message.headers['x-txn-id']), str)

        await udsource.ack_handler(AckRequest([source_message.offset]))

        filter_resize_message = await apply_map(
            filter_resize,
            source_message,
            source_message.headers,
        )

        self.assertIs(type(filter_resize_message.value), bytes)
        self.assertEqual(len(filter_resize_message.keys), 3)
        self.assertEqual(filter_resize_message.keys[0], '0')
        self.assertEqual(filter_resize_message.keys[1], '2160')
        self.assertEqual(filter_resize_message.keys[2], '3840')

        inference_message = await apply_map(
            inference,
            filter_resize_message,
            source_message.headers,
        )

        self.assertIs(type(inference_message.value), bytes)
        self.assertEqual(len(inference_message.keys), 3)
        self.assertEqual(inference_message.keys[0], '0')
        self.assertEqual(inference_message.keys[1], '2160')
        self.assertEqual(inference_message.keys[2], '3840')

        sink_output = await output_to_sink(udsink, inference_message, source_message.headers, 'foo')

        self.assertEqual(len(sink_output), 1)
        self.assertEqual(sink_output[0].id, 'foo')
        self.assertTrue(sink_output[0].success)

        ######################################################################
        # Try to flow the second frame but no more
        ######################################################################
        with self.assertRaises(StopAsyncIteration):
            await input_from_source(udsource)
