import os
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

class KafkaClient:
    def __init__(self):
        self.bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
        self.consumer = None
        self.producer = None

    async def start(self):
        # consumer created in WorkerConsumer to allow custom group_id and topics
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap)
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            self.producer = None
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

    async def send(self, topic: str, key: str, value: dict):
        if not self.producer:
            raise RuntimeError("Producer not started")
        await self.producer.send_and_wait(topic, json.dumps(value).encode(), key=(key or "").encode())

    # helper to create a consumer externally (used by WorkerConsumer)
    def create_consumer(self, topics, group_id):
        return AIOKafkaConsumer(
            *topics,
            loop=None,
            bootstrap_servers=self.bootstrap,
            group_id=group_id,
            enable_auto_commit=True,
            auto_offset_reset="earliest"
        )
