import subprocess
import time
from threading import Timer

from pynumaflow import setup_logging
from pynumaflow.proto.sourcer import source_pb2

_logger = setup_logging(__name__)


def request_generator(count, session=1, handshake=True):
    if handshake:
        yield source_pb2.ReadRequest(handshake=source_pb2.Handshake(sot=True))

    for _j in range(session):
        for _i in range(count):
            req = source_pb2.ReadRequest(
                request=source_pb2.ReadRequest.Request(num_records=1),
            )
            yield req


def launch_mediamtx_and_wait_ready() -> subprocess.Popen:
    p = subprocess.Popen(
        [
            './mediamtx',
            './mediamtx.yml.template',
        ],
        cwd='../../video-streaming-server/mediamtx',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    run = False

    def kill_process(p) -> None:
        p.kill()

    t = Timer(10, kill_process, [p])
    t.start()

    while not run:
        _logger.info('waiting for mediamtx......')
        time.sleep(1)

        while True:
            if p.poll() is not None:
                msg = 'mediamtx not running or timeout error'
                raise ValueError(msg)

            line = p.stdout.readline()
            _logger.info(line.strip().decode())
            if b'INF [RTSP] listener opened on' in line:
                _logger.info('started mediamtx')
                run = True
                t.cancel()
                break

    return p
