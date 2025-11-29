import os, json, asyncio
from aiokafka import AIOKafkaProducer

class KafkaProducer:
    def __init__(self):
        self._producer = None
        self.bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    async def start(self):
        if not self._producer:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap)
            await self._producer.start()

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def send(self, topic: str, key: str, value: dict):
        if not self._producer:
            await self.start()
        await self._producer.send_and_wait(topic, json.dumps(value).encode(), key=key.encode())

kafka_producer = KafkaProducer()

