import asyncio
import json
import logging
from typing import Callable, Awaitable

from aiokafka import AIOKafkaConsumer

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}

    def register_handler(self, topic_pattern: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._handlers[topic_pattern] = handler

    async def start(self) -> None:
        try:
            self._consumer = AIOKafkaConsumer(
                "tenant.#",
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id="saas-backend-audit-logger",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await self._consumer.start()
            logger.info("Kafka consumer started")

            # Start consuming in background
            asyncio.create_task(self._consume_loop())
        except Exception as e:
            logger.warning(f"Kafka consumer failed to start: {e}")
            self._consumer = None

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        if self._consumer is None:
            return
        try:
            async for message in self._consumer:
                topic = message.topic
                value = message.value
                logger.debug(f"Received Kafka message on {topic}: {value.get('action', 'unknown')}")
                # Audit log handler - just log for now
                logger.info(
                    f"[AUDIT] tenant={value.get('tenant_id')} "
                    f"entity={value.get('entity')} action={value.get('action')} "
                    f"payload={value.get('payload')}"
                )
        except Exception as e:
            logger.error(f"Kafka consumer loop error: {e}")


kafka_consumer = KafkaConsumer()