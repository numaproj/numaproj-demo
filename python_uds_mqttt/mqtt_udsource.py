import os
import asyncio
import uuid
from datetime import datetime
import logging

from aiomqtt import Client
from pynumaflow.shared.asynciter import NonBlockingIterator
from pynumaflow.sourcer import (
    ReadRequest,
    Message,
    AckRequest,
    PendingResponse,
    Offset,
    PartitionsResponse,
    get_default_partitions,
    Sourcer,
    SourceAsyncServer,
    NackRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MQTTAsyncSource(Sourcer):
    """
    User-defined source for MQTT messages.
    """

    def __init__(self, broker, port, topic):
        # The offset idx till where the messages have been read
        self.read_idx: int = 0
        # Set to maintain a track of the offsets yet to be acknowledged
        self.to_ack_set: set[int] = set()
        # Set to maintain a track of the offsets that have been negatively acknowledged
        self.nacked: set[int] = set()
        # MQTT broker address to connect to.
        self.broker = broker
        # Port number of the MQTT broker.
        self.port = port
        # MQTT topic to subscribe to for receiving messages.
        self.topic = topic
        # Async queue to store incoming messages
        self.messages = asyncio.Queue()
        # Asyncio task for MQTT client loop
        self._mqtt_task = None
        # Flag indicating if source has started
        self._started = False

    async def start_mqtt_consumer(self):
        """Start the MQTT consumer"""
        if self._started:
            return
        self._started = True
        
        logger.info(f"Starting MQTT consumer for broker={self.broker}, port={self.port}, topic={self.topic}")
        
        async def mqtt_loop():
            while True:
                try:
                    async with Client(self.broker, self.port) as client:
                        await client.subscribe(self.topic)
                        logger.info(f"Successfully subscribed to MQTT topic: {self.topic}")
                        async for msg in client.messages:
                            payload = msg.payload.decode()
                            logger.info(f"Received MQTT message: {payload}")
                            await self.messages.put(payload)
                except Exception as e:
                    logger.error(f"MQTT consumer error: {e}. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
        
        self._mqtt_task = asyncio.create_task(mqtt_loop())

    async def read_handler(self, datum: ReadRequest, output: NonBlockingIterator):
        """
        read_handler is used to read the data from the source and send the data forward
        for each read request we process num_records and increment the read_idx to indicate that
        the message has been read and the same is added to the ack set
        """

        if not self._started:
            await self.start_mqtt_consumer()
        
        if len(self.to_ack_set) >= 500:
            return

        for _ in range(datum.num_records):
            if self.nacked:
                idx = self.nacked.pop()
            else:
                idx = self.read_idx
                self.read_idx += 1

            try:
                payload = self.messages.get_nowait()
                logger.info(f"Sending MQTT message: {payload}")
            except asyncio.QueueEmpty:
                payload = f"dummy-{idx}"

            headers = {"x-txn-id": str(uuid.uuid4())}
            await output.put(
                Message(
                    payload=str(payload).encode(),
                    offset=Offset.offset_with_default_partition_id(str(idx).encode()),
                    event_time=datetime.now(),
                    headers=headers,
                )
            )
            self.to_ack_set.add(idx)

    async def ack_handler(self, ack_request: AckRequest):
        """
        Handle message acknowledgments.
        """
        for req in ack_request.offsets:
            offset = int(req.offset)
            self.to_ack_set.remove(offset)

    async def nack_handler(self, ack_request: NackRequest):
        """
        Add the offsets that have been negatively acknowledged to the nacked set
        """

        for req in ack_request.offsets:
            offset = int(req.offset)
            self.to_ack_set.remove(offset)
            self.nacked.add(offset)
        logger.info("Negatively acknowledged offsets: %s", self.nacked)

    async def pending_handler(self) -> PendingResponse:
        """
        Return the number of pending messages in the queue
        """
        return PendingResponse(count=self.messages.qsize())

    async def partitions_handler(self) -> PartitionsResponse:
        """
        Return default partitions.
        """
        return PartitionsResponse(partitions=get_default_partitions())


if __name__ == "__main__":
    broker = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", 1883))
    topic = os.getenv("MQTT_TOPIC", "test")

    logger.info(f"Configuring MQTT Source: broker={broker}, port={port}, topic={topic}")
    
    ud_source = MQTTAsyncSource(broker, port, topic)
    grpc_server = SourceAsyncServer(ud_source, sock_path="/var/run/numaflow/source.sock")
    
    logger.info("Starting MQTT UDS gRPC server")
    grpc_server.start()