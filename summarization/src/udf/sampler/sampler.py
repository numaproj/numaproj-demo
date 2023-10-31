import json
import logging
from typing import Iterable, Iterator, AsyncIterable
import nltk
from nltk.tokenize import word_tokenize

from pynumaflow.mapper import (
    Datum,
    Message,
    Messages,
)
from pynumaflow.reducer import Metadata
from pynumaflow.sourcetransformer import Messages as MessageTs
from pynumaflow.sourcetransformer import Message as MessageT

logger = logging.getLogger(__name__)
log_patterns = ["level=info", "level=warn", "level=error", "level=fatal"]
nltk.download("punkt")
FILE = "/var/numaflow/side-inputs/metrics"


def map_logs_transformer(keys: list[str], datum: Datum) -> MessageTs:
    """
    Extract the keys from the message and prepare them for the reduce step
    param keys: list of keys to be used for the reduce step
    param datum: the incoming message, the expected format is as follows:
    {
        “ts”: 1692036005,
        “tid”: VADE0B248932
        “start_time”: 1692036005,
        “end_time”: 1692036005,
        “app_name”: “my-app”,
        “app_type”: “Deployment”,
        “summarization_type”: “pod”,
        “summarization_name”: “osam-customer-interaction-pr-53”
        “logs”: [
            “2023/08/14 21:07:03.515 INFO  c.i.o.o.generic.transform.ToJSONDoFn…”,
            “2023/08/14 21:07:03.211 INFO  c.i.o.o.g.t.CombineByKeyFn$PrintCombined…”,
                    …
        ]
    }
    """
    logger.info("Map logs transformer called")
    val = datum.value
    # val_json = json.loads(val.decode("utf-8"))
    try:
        val_json = json.loads(val)
    except Exception as ex:
        logger.error(
            "Error during json parsing", str(ex), stack_info=True, exc_info=True
        )
        logger.error("Error during json parsing, message value: ", str(val))
        return Messages(Message.to_drop())
    event_time = datum.event_time

    # Keys for the entire application summarization
    map_keys_overall = [
        val_json.get("namespace"),
        val_json.get("app_type"),
        val_json.get("app_name"),
    ]

    # Keys for the individual pods summarization
    map_keys_detail = [
        val_json.get("namespace"),
        val_json.get("summarization_type"),
        val_json.get("summarization_name"),
    ]

    logger.info("Map logs transformer called with keys: %s", map_keys_detail)
    messages = MessageTs()
    # Generate two massages, one for the overall summarization and one for the individual pods
    messages.append(MessageT(val, keys=map_keys_detail, event_time=event_time))
    messages.append(MessageT(val, keys=map_keys_overall, event_time=event_time))
    return messages


def jaccard_distance(a, b):
    """
    Compute the Jaccard distance between two sets a and b
    """
    union = len(a.union(b))
    if union == 0:
        return 1
    return 1 - len(a.intersection(b)) / union


def compute_clusters(logs, jaccard_distance_threshold=0.4, to_drop=True):
    """
    Compute clusters of logs based on the Jaccard distance
    """
    clusters = []

    for i, log in enumerate(logs):
        tokens = set(word_tokenize(log))

        log_type = (
            "info"
            if "level=info" in log
            else "error"
            if "level=error" in log
            else "warn"
            if "level=warn" in log
            else "fatal"
            if "level=fatal" in log
            else "drop"
        )
        if to_drop and log_type == "drop":
            continue
        else:
            if log_type == "drop":
                log_type = "info"

        min_distance = 2
        cluster_index = -1

        for c, cluster in enumerate(clusters):
            jd = jaccard_distance(tokens, cluster["tokens"])
            if jd < min_distance:
                min_distance = jd
                cluster_index = c

        if min_distance <= jaccard_distance_threshold:
            clusters[cluster_index]["log"] = log
            clusters[cluster_index]["tokens"] = tokens
            clusters[cluster_index]["members"].append(i)
        else:
            cluster = {"log": log, "tokens": tokens, "type": log_type, "members": [i]}
            clusters.append(cluster)

    for cluster in clusters:
        cluster["logs_count"] = len(cluster["members"])
        del cluster["members"]
        del cluster["tokens"]

    clusters.sort(key=lambda c: c.get("type"))

    return clusters


def log_type_counter(clusters):
    """
    Count the number of logs per type
    """
    counter = {"info": 0, "warn": 0, "error": 0, "fatal": 0}
    for cluster in clusters:
        counter[cluster["type"]] += cluster["logs_count"]
    return counter


def aggregate_logs(datums: Iterable[Datum]) -> Iterator[str]:
    """
    Extract the logs from the message and prepare them for the reduce step, return a generator of logs
    """
    for datum in datums:
        val = datum.value
        val_json = json.loads(val.decode("utf-8"))
        for log in val_json.get("logs"):
            yield log


def cluster_summary_logs(clusters: list[dict]) -> str:
    summary = ""

    for i, c in enumerate(clusters):
        summary += (
            f"Log type: {c['type']}, log count: {c['logs_count']}, log sample: {c['log']}"
            + "\n"
        )

    return summary


def cluster_summary_events(clusters: list[dict]) -> str:
    summary = ""
    for i, c in enumerate(clusters):
        summary += f" {c['log']}" + "\n"

    return summary


def get_scores(file: str, namespace: str, app_name: str, app_type: str):
    with open(file, "rb") as f:
        try:
            data = f.read().decode("utf-8")
            json_data = json.loads(data)
            dict_scores = {}
            if json_data:
                for item in json_data:
                    if (
                        item.get("namespace") == namespace
                        and item.get("appName") == app_name
                        and item.get("appType") == app_type
                    ):
                        dict_scores[item.get("name")] = item.get("value")
            return dict_scores
        except Exception as ex:
            logger.error(
                "Error during json parsing", str(ex), stack_info=True, exc_info=True
            )
            return {}


async def sample_logs_handler(
    keys: list[str], datums: AsyncIterable[Datum], md: Metadata
) -> Messages:
    logs = []
    events = []
    app_name = ""
    app_type = ""
    namespace = ""
    async for datum in datums:
        val = datum.value
        logger.info("val is : %s", val)
        if not val:
            continue
        val_json = json.loads(val.decode("utf-8"))
        if not val_json:
            continue
        app_name = val_json.get("app_name")
        app_type = val_json.get("app_type")
        namespace = val_json.get("namespace")
        if not val_json.get("logs"):
            continue
        for log in val_json.get("logs"):
            logs.append(log)
        if val_json.get("events"):
            for event in val_json.get("events"):
                events.append(event)

    logger.info("len is : %s, %s", len(logs), len(events))
    clusters_logs = compute_clusters(logs, to_drop=True)
    log_counter = log_type_counter(clusters_logs)
    clusters_events = compute_clusters(events, to_drop=False)
    metric_scores = get_scores(FILE, namespace, app_name, app_type)
    msg = {
        "namespace": namespace,
        "app_name": app_name,
        "app_type": app_type,
        "info_count": log_counter.get("info"),
        "warn_count": log_counter.get("warn"),
        "error_count": log_counter.get("error"),
        "fatal_count": log_counter.get("fatal"),
        "log_clusters": clusters_logs,
        "log_sample": cluster_summary_logs(clusters_logs),
        "event_sample": cluster_summary_events(clusters_events),
        "metric_scores": metric_scores,
    }

    msg_str = json.dumps(msg)
    logger.info("Clustered logs: %s", msg_str)

    return Messages(Message(str.encode(msg_str), keys=keys))
