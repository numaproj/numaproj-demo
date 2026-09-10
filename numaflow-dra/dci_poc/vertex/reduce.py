from collections.abc import AsyncIterable

import msgspec
from pynumaflow.accumulator import (
    Accumulator,
    AccumulatorAsyncServer,
    Datum,
    Message,
)
from pynumaflow.shared.asynciter import NonBlockingIterator
from sortedcontainers import SortedDict

from lib.log import setup_logging
from lib.message_spec import Payload

_logger = None


def setup_logger():
    global _logger
    if _logger is None:
        _logger = setup_logging(__name__)


class StreamJoiner(Accumulator):
    def __init__(self):
        setup_logger()
        _logger.info('Reduce initialized')

        self.latest_frame_idx = -1
        self.sorted_source_frames = SortedDict()
        self.sorted_inference_results = SortedDict()

    async def handler(self, datums: AsyncIterable[Datum], output: NonBlockingIterator):
        async for datum in datums:
            payload = msgspec.msgpack.decode(datum.value, type=Payload)
            frame_idx = payload.frame_index

            # Whether the datum is from inference or source.
            if payload.compressed_frame is None:
                # The datum is from inference.
                # Check whether there is a matched frame or not.
                if frame_idx in self.sorted_source_frames:
                    # A matched frame is found.
                    datum_source = self.sorted_source_frames.pop(frame_idx)
                    await self.merge_and_output(output, datum_source, datum)
                    _logger.info(f'inference result {frame_idx} has gone with matched source frame')
                else:
                    self.sorted_inference_results[frame_idx] = datum
                    _logger.info(f'inference result {frame_idx} has arrived')
                # Remove old source frames never being used.
                num_old_frames = self.sorted_source_frames.bisect_right(frame_idx)
                for _ in range(num_old_frames):
                    self.sorted_source_frames.popitem(index=0)
                _logger.info(f'{num_old_frames} old source frames have been GCed')
            else:
                # The datum is from source.
                # Check whether there is a matched inference result or not.
                if frame_idx in self.sorted_inference_results:
                    # A matched inference result is found.
                    datum_inference = self.sorted_inference_results.pop(frame_idx)
                    await self.merge_and_output(output, datum, datum_inference)
                    _logger.info(f'source frame {frame_idx} has gone with matched inference result')
                else:
                    self.sorted_source_frames[frame_idx] = datum
                    _logger.info(f'source frame {frame_idx} has arrived')
                # Remove old inference results never being used.
                num_old_results = self.sorted_inference_results.bisect_right(frame_idx)
                for _ in range(num_old_results):
                    self.sorted_inference_results.popitem(index=0)
                _logger.info(f'{num_old_results} old inference results have been GCed')

            self.latest_frame_idx = max(self.latest_frame_idx, frame_idx)
            _logger.info(f'latest frame index: {self.latest_frame_idx}')
            _logger.info(
                f'frames={len(self.sorted_source_frames)}, '
                f'results={len(self.sorted_inference_results)}'
            )

        _logger.info('out of datums loop')

    async def merge_and_output(
        self,
        output: NonBlockingIterator,
        datum_source: Datum,
        datum_inference: Datum,
    ) -> None:
        # Merge two payloads
        payload_source = msgspec.msgpack.decode(datum_source.value, type=Payload)
        payload_inference = msgspec.msgpack.decode(datum_inference.value, type=Payload)
        payload_out = Payload(
            frame_index=payload_source.frame_index,
            bounding_boxes=payload_inference.bounding_boxes,
            compressed_frame=payload_source.compressed_frame,
        )

        # Output a message with fields (except value) restored from source
        await output.put(
            Message(
                keys=datum_source.keys,
                value=msgspec.msgpack.encode(payload_out),
                watermark=datum_source.watermark,
                event_time=datum_source.event_time,
                headers=datum_source.headers,
                id=datum_source.id,
            )
        )


if __name__ == '__main__':
    grpc_server = AccumulatorAsyncServer(StreamJoiner)
    grpc_server.start()
