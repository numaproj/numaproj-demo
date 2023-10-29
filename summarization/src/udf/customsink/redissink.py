import json
import logging
import os
import time
from collections.abc import Iterator

from pynumaflow.sinker import Responses, Response
from redis.backoff import ExponentialBackoff
from redis.exceptions import RedisClusterException, RedisError
from redis.retry import Retry
from redis.sentinel import Sentinel, MasterNotFoundError
from pynumaflow.mapper import Datum

logger = logging.getLogger(__name__)


class RedisSink:
    @staticmethod
    def get_redis_client(
        host: str,
        port: int,
        password: str,
        mastername: str,
        master_node: bool = True,
    ) -> Sentinel:
        """
        Return a master redis client for sentinel connections, with retry.

        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            mastername: Redis sentinel master name
            master_node: Whether to use the master node or the slave nodes

        Returns
        -------
            Redis client instance
        """

        retry = Retry(
            ExponentialBackoff(),
            3,
            supported_errors=(
                ConnectionError,
                TimeoutError,
                RedisClusterException,
                RedisError,
                MasterNotFoundError,
            ),
        )

        conn_kwargs = {
            "socket_timeout": 1,
            "socket_connect_timeout": 1,
            "socket_keepalive": True,
            "health_check_interval": 10,
        }

        sentinel = Sentinel(
            [(host, port)],
            sentinel_kwargs=dict(password=password, **conn_kwargs),
            retry=retry,
            password=password,
            **conn_kwargs,
        )
        if master_node:
            sentinel_client = sentinel.master_for(mastername)
        else:
            sentinel_client = sentinel.slave_for(mastername)
        logger.info(
            "Sentinel redis params: %s, master_node: %s", conn_kwargs, master_node
        )
        return sentinel_client

    def __init__(self):
        self.redis_host = app_id = os.getenv("REDIS_HOST", None)
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_cred = os.getenv("REDIS_CRED", None)
        self.redis_mastername = os.getenv("REDIS_MASTERNAME", None)
        self.key_prefix = os.getenv("KEY_PREFIX", "")
        if self.key_prefix:
            self.key_prefix += ":"

        self.redis_client = self.get_redis_client(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_cred,
            mastername=self.redis_mastername,
        )

    def udsink(self, datums: Iterator[Datum]) -> Responses:
        responses = Responses()
        try:
            for msg in datums:
                body = msg.value.decode("utf-8")
                if not body:
                    logger.error("No body found in the message")
                    responses.append(Response.as_success(msg.id))
                    continue

                json_body = json.loads(body)

                key_list = json_body.get("keys")
                if not key_list:
                    logger.error("No keys found in the message")
                    responses.append(Response.as_success(msg.id))
                    continue

                key = self.key_prefix + ":".join(key_list)

                if json_body.get("data_payload"):
                    timestamp_ = int(time.time())
                    self.redis_client.zadd(
                        key, {json.dumps(json_body.get("data_payload")): timestamp_}
                    )
                    logger.info("Redis stored message with a key: %s", key)
                responses.append(Response.as_success(msg.id))
        except Exception as e:
            logger.error(
                "Error in udsink_handler: %s", str(e), exc_info=True, stack_info=True
            )
            responses.append(Response.as_failure(msg.id, str(e)))
        return responses
