import sys
import logging

import aiorun
from pynumaflow.mapper import Mapper
from pynumaflow.reducer import AsyncReducer

from factory import UDFFactory
from pynumaflow.sinker import Sinker
from pynumaflow.sourcetransformer import SourceTransformer


def configure_logger():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # see logs from other libraries
    root = logging.getLogger()
    # remove handlers created by libraries e.g. mlctl
    # copy the list because this mutates it
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)


configure_logger()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"starter - STARTED. sys.argv={str(sys.argv)}")
    step_handler, handler_type = UDFFactory.get_handler(sys.argv[1])

    if handler_type == "transformer":
        grpc_server = SourceTransformer(handler=step_handler)
        grpc_server.start()
    elif handler_type == "reducer":
        grpc_server = AsyncReducer(handler=step_handler)
        aiorun.run(grpc_server.start())
    elif handler_type == "sink":
        grpc_server = Sinker(handler=step_handler)
        grpc_server.start()
    else:
        # Regular UDF
        grpc_server = Mapper(handler=step_handler)
        grpc_server.start()
