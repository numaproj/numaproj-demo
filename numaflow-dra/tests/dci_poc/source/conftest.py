from threading import Timer

import pytest
from pynumaflow import setup_logging
from pynumaflow.proto.sourcer import source_pb2_grpc
from pynumaflow.sourcer import (
    SourceAsyncServer,
)
from tests.dci_poc.source.utils import (
    launch_ffmpeg_and_wait_ready,
    launch_mediamtx_and_wait_ready,
)

from dci_poc.vertex.source import AsyncSourceSendFrame

logger = setup_logging(__name__)


@pytest.fixture
def source_handler() -> AsyncSourceSendFrame:
    handler = AsyncSourceSendFrame()

    yield handler

    handler.stop_reader()


@pytest.fixture
def source_servicer_impl(source_handler) -> source_pb2_grpc.SourceServicer:
    server = SourceAsyncServer(source_handler)
    udf = server.servicer
    return udf


@pytest.fixture
def setup_video_streaming() -> None:
    try:
        mediamtx = launch_mediamtx_and_wait_ready()
        ffmpeg = launch_ffmpeg_and_wait_ready()

        ffmpeg.stdout.close()

        def kill_process(p) -> None:
            p.kill()

        t = Timer(10, kill_process, [mediamtx])
        t.start()

        while True:
            if mediamtx.poll() is not None:
                msg = 'mediamtx ready timeout error'
                raise ValueError(msg)

            line = mediamtx.stdout.readline()
            logger.info(line.strip().decode())
            if b'INF [path my_stream] [MPEG-TS source] ready' in line:
                t.cancel()
                break

        yield
    finally:
        try:
            if ffmpeg is not None:
                logger.info('terminate ffmpeg')
                ffmpeg.kill()
        except Exception as e:
            logger.error(e)
        try:
            if mediamtx is not None:
                logger.info('terminate mediamtx')
                mediamtx.kill()
        except Exception as e:
            logger.error(e)
