import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            logger.info("Kafka producer started")
        except Exception as e:
            logger.warning(f"Kafka producer failed to start: {e}")
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        if self._producer is None:
            logger.warning(f"Kafka producer not available, skipping event on {topic}")
            return
        try:
            await self._producer.send_and_wait(topic, value=event, key=event.get("tenant_id", ""))
            logger.debug(f"Published event to {topic}: {event.get('action')}")
        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {e}")


kafka_producer = KafkaProducer()