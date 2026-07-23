import json
import logging
import threading
import time

from app.core.config import settings
from app.repositories import upsert_profile

try:
    import boto3
except ImportError:  # pragma: no cover - dependency is installed in runtime image
    boto3 = None

LOGGER = logging.getLogger("profile-service")
_stop_consumer = threading.Event()


def consume_user_events() -> None:
    if not settings.USER_EVENTS_QUEUE_URL or boto3 is None:
        LOGGER.info("SQS is not configured; profile event consumer disabled")
        return
    client = boto3.client("sqs", region_name=settings.AWS_REGION)
    while not _stop_consumer.is_set():
        try:
            response = client.receive_message(
                QueueUrl=settings.USER_EVENTS_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10,
                VisibilityTimeout=30,
            )
            for message in response.get("Messages", []):
                body = json.loads(message["Body"])
                if body.get("type") == "UserRegistered":
                    upsert_profile(body["user_id"], body["email"], body["display_name"])
                client.delete_message(
                    QueueUrl=settings.USER_EVENTS_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"],
                )
        except Exception:
            LOGGER.exception("failed to consume user event")
            time.sleep(5)


def start_consumer() -> None:
    threading.Thread(target=consume_user_events, daemon=True).start()


def stop_consumer() -> None:
    _stop_consumer.set()
