import json
import logging
from typing import Any

from app.core.config import settings

try:
    import boto3
except ImportError:  # pragma: no cover - dependency is installed in runtime image
    boto3 = None

LOGGER = logging.getLogger("auth-service")


def publish_user_registered(user: dict[str, Any]) -> None:
    if not settings.USER_EVENTS_QUEUE_URL or boto3 is None:
        LOGGER.info("SQS is not configured; skipping UserRegistered event")
        return
    client = boto3.client("sqs", region_name=settings.AWS_REGION)
    client.send_message(
        QueueUrl=settings.USER_EVENTS_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "type": "UserRegistered",
                "user_id": str(user["id"]),
                "email": user["email"],
                "display_name": user["display_name"],
            }
        ),
    )
