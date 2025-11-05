import asyncio

import pytest
import requests
from pynumaflow import setup_logging
from pynumaflow.mapstreamer import MapStreamAsyncServer, MapStreamer
from pynumaflow.proto.mapper import map_pb2_grpc
from pynumaflow.proto.sinker import sink_pb2_grpc
from pynumaflow.proto.sourcer import source_pb2_grpc
from pynumaflow.sinker import SinkAsyncServer, Sinker
from pynumaflow.sourcer import SourceAsyncServer, Sourcer
from tests.testing_utils import (
    start_event_loop_thread,
    start_map_server,
    start_sink_server,
    start_source_server,
    stop_event_loop_thread,
    stop_map_server,
    stop_sink_server,
    stop_source_server,
    wait_for_channnel_ready,
)

_logger = setup_logging(__name__)


class DummySourceIpml(Sourcer):
    pass


class DummyMapIpml(MapStreamer):
    pass


class DummySinkIpml(Sinker):
    pass


@pytest.fixture
def source_servicer_impl() -> source_pb2_grpc.SourceServicer:
    handler = DummySourceIpml()
    server = SourceAsyncServer(handler)
    udf = server.servicer
    return udf


@pytest.fixture
def map_servicer_impl() -> map_pb2_grpc.MapServicer:
    handler = DummyMapIpml()
    server = MapStreamAsyncServer(handler)
    udf = server.servicer
    return udf


@pytest.fixture
def sink_servicer_impl() -> sink_pb2_grpc.SinkServicer:
    handler = DummySinkIpml()
    server = SinkAsyncServer(handler)
    udf = server.servicer
    return udf


@pytest.fixture
def source_stub(source_servicer_impl) -> source_pb2_grpc.SourceStub:
    """
    start grpc server in thread event loop, and then return SourceStub.
    """
    # === SetUp ===
    # start event loop/thread
    loop, thread = start_event_loop_thread()

    socket = 'unix:///tmp/source.sock'
    # execute map server(coroutin that is defined in async def) to event loop.
    # return Future means a box to store the result of a coroutine execution.
    # Future allow result of coroutin to be checked in caller thread(here).
    server_future = asyncio.run_coroutine_threadsafe(
        start_source_server(socket=socket, udf=source_servicer_impl),
        loop=loop,
    )

    server = server_future.result(timeout=10.0)
    channel = wait_for_channnel_ready(socket=socket)

    try:
        # For Test
        yield source_pb2_grpc.SourceStub(channel)
    finally:
        # === TearDown ===
        # close channel -> stop server -> stop event loop/thread
        try:
            channel.close()
        except Exception as e:
            _logger.warning('failed to close channel: %s', e)

        try:
            future = asyncio.run_coroutine_threadsafe(
                stop_source_server(server, grace=1.0),
                loop=loop,
            )
            future.result(timeout=5.0)
        except Exception as e:
            _logger.warning('failed to stop server: %s', e)

        stop_event_loop_thread(loop, thread)


@pytest.fixture
def map_stub(map_servicer_impl) -> map_pb2_grpc.MapStub:
    """
    start grpc server in thread event loop, and then return MapStub.
    """
    # === SetUp ===
    # start event loop/thread
    loop, thread = start_event_loop_thread()

    socket = 'unix:///tmp/async_map_stream.sock'
    # execute map server(coroutin that is defined in async def) to event loop.
    # return Future means a box to store the result of a coroutine execution.
    # Future allow result of coroutin to be checked in caller thread(here).
    server_future = asyncio.run_coroutine_threadsafe(
        start_map_server(socket=socket, udf=map_servicer_impl),
        loop=loop,
    )

    server = server_future.result(timeout=10.0)
    channel = wait_for_channnel_ready(socket=socket)

    try:
        # For Test
        yield map_pb2_grpc.MapStub(channel)
    finally:
        # === TearDown ===
        # close channel -> stop server -> stop event loop/thread
        try:
            channel.close()
        except Exception as e:
            _logger.warning('failed to close channel: %s', e)

        try:
            future = asyncio.run_coroutine_threadsafe(
                stop_map_server(server, grace=1.0),
                loop=loop,
            )
            future.result(timeout=5.0)
        except Exception as e:
            _logger.warning('failed to stop server: %s', e)

        stop_event_loop_thread(loop, thread)


@pytest.fixture
def sink_stub(sink_servicer_impl) -> sink_pb2_grpc.SinkStub:
    """
    start grpc server in thread event loop, and then return SinkStub.
    """
    # === SetUp ===
    # start event loop/thread
    loop, thread = start_event_loop_thread()

    socket = 'unix:///tmp/sink.sock'
    # execute map server(coroutin that is defined in async def) to event loop.
    # return Future means a box to store the result of a coroutine execution.
    # Future allow result of coroutin to be checked in caller thread(here).
    server_future = asyncio.run_coroutine_threadsafe(
        start_sink_server(socket=socket, udf=sink_servicer_impl),
        loop=loop,
    )

    server = server_future.result(timeout=10.0)
    channel = wait_for_channnel_ready(socket=socket)

    try:
        # For Test
        yield sink_pb2_grpc.SinkStub(channel)
    finally:
        # === TearDown ===
        # close channel -> stop server -> stop event loop/thread
        try:
            channel.close()
        except Exception as e:
            _logger.warning('failed to close channel: %s', e)

        try:
            future = asyncio.run_coroutine_threadsafe(
                stop_sink_server(server, grace=1.0),
                loop=loop,
            )
            future.result(timeout=5.0)
        except Exception as e:
            _logger.warning('failed to stop server: %s', e)

        stop_event_loop_thread(loop, thread)


# sink.py
@pytest.fixture(autouse=True)
def mock_requests_post(monkeypatch):
    def dummy_post(*_args, **_kwargs):
        class DummyResponse:
            status_code = 200
            text = 'mocked response'

            def json(self):
                return {'count': -1}

        return DummyResponse()

    monkeypatch.setattr(requests, 'post', dummy_post)
