import logging

logger = logging.getLogger(__name__)


class UDFFactory:
    """Factory class to return the handler for the given step."""

    @classmethod
    def get_handler(cls, step: str) -> (callable, str):
        """
        Return the handler for the given step. supports the following steps:
        - map_logs
        - sample_logs
        - genai_processor
        """
        logger.info("factory:get_handler - step=" + step)

        if step == "map_logs":
            from udf.sampler.sampler import map_logs_transformer

            return map_logs_transformer, "transformer"

        if step == "sample_logs":
            from udf.sampler.sampler import sample_logs_handler

            return sample_logs_handler, "reducer"

        if step == "genai_processor":
            from udf.processor.processor import Processor

            processor = Processor(temperature=0.25)
            return processor.udf, "handler"

        if step == "redis_sink":
            from udf.customsink.redissink import RedisSink

            redis_sink = RedisSink()
            return redis_sink.udsink, "sink"

        raise NotImplementedError(f"Invalid step provided: {step}")
