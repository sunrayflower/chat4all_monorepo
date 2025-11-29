import asyncio
import json
import os
import time
import math
from aiokafka import AIOKafkaConsumer
from .kafka_client import KafkaClient
from .db import messages_collection, redis
from .adapter_client import AdapterClient, AdapterError

# Prometheus metrics for worker
from prometheus_client import Counter, Histogram

JOB = "worker"
KAFKA_CONSUMED = Counter('kafka_consumed_messages_total', 'Consumed Kafka messages', ['job'])
KAFKA_PRODUCED = Counter('kafka_produced_messages_total', 'Produced Kafka messages', ['job','topic'])
WORKER_PROCESS_SECONDS = Histogram('worker_process_seconds', 'Worker processing time', ['job'])
DEDUP_HITS = Counter('redis_dedup_hits_total', 'Dedup hits (redis)', ['job'])

class WorkerConsumer:
    def __init__(self, kafka_client: KafkaClient, http_session):
        self.running = False
        self.kafka_client = kafka_client
        self.http_session = http_session
        self.adapter_client = AdapterClient(http_session)
        self.consumer = None
        self.task = None
        self.incoming_topic = os.getenv("INCOMING_TOPIC", "incoming.messages")
        self.outgoing_topic = os.getenv("OUTGOING_TOPIC", "outgoing.messages")
        self.dlq_topic = os.getenv("DLQ_TOPIC", "deadletters")
        self.group_id = os.getenv("WORKER_GROUP_ID", "chat4all-router-group")
        # retry policy
        self.max_retries = int(os.getenv("MAX_RETRIES", "5"))
        self.base_backoff = float(os.getenv("BASE_BACKOFF", "0.5"))  # seconds

    async def start(self):
        self.consumer = self.kafka_client.create_consumer([self.incoming_topic], group_id=self.group_id)
        await self.consumer.start()
        self.kafka_client.consumer = self.consumer  # optionally expose
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        print("WorkerConsumer started and listening for messages")

    async def stop(self):
        self.running = False
        if self.task:
            await self.task
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

    async def _run_loop(self):
        async for msg in self.consumer:
            if not self.running:
                break
            try:
                payload = json.loads(msg.value.decode())
            except Exception as e:
                print("invalid message payload", e)
                continue
            # process in background to keep consumer loop responsive
            asyncio.create_task(self._handle_message(payload))

    async def _handle_message(self, message: dict):
        msg_id = message.get("message_id")
        if not msg_id:
            print("skipping message without message_id")
            return

        start_time = time.time()
        KAFKA_CONSUMED.labels(job=JOB).inc()

        dedup_key = f"worker:dedup:{msg_id}"
        was_set = await redis.set(dedup_key, "1", ex=60*60, nx=True)
        if not was_set:
            DEDUP_HITS.labels(job=JOB).inc()
            print(f"message {msg_id} already processed (dedup)")
            return

        await messages_collection.update_one({"message_id": msg_id}, {"$set": {"state": "PROCESSING", "updated_at": time.time()}}, upsert=True)

        recipients = message.get("recipient_ids") or []
        channel_hint = message.get("channel_hint")
        successes = []
        failures = []
        for rid in recipients:
            try:
                adapter_base = self.adapter_client.resolve_adapter_base(channel_hint, rid)
                attempt = 0
                while True:
                    try:
                        attempt += 1
                        await self.adapter_client.send_to_adapter(adapter_base, message, rid)
                        successes.append(rid)
                        break
                    except AdapterError as e:
                        if attempt > self.max_retries:
                            failures.append({"recipient": rid, "error": str(e)})
                            break
                        backoff = self.base_backoff * (2 ** (attempt - 1)) * (1 + 0.1 * (attempt - 1))
                        await asyncio.sleep(backoff)
                    except Exception as e:
                        if attempt > self.max_retries:
                            failures.append({"recipient": rid, "error": str(e)})
                            break
                        backoff = self.base_backoff * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)
            except Exception as e:
                failures.append({"recipient": rid, "error": str(e)})

        new_state = "DELIVERED" if len(failures) == 0 else "PARTIAL" if len(successes) > 0 else "FAILED"
        await messages_collection.update_one({"message_id": msg_id}, {"$set": {"state": new_state, "delivered_to": successes, "failed_to": failures, "updated_at": time.time()}}, upsert=True)

        for rid in successes:
            event = {"message_id": msg_id, "recipient_id": rid, "status": "delivered", "timestamp": time.time()}
            await self.kafka_client.send(self.outgoing_topic, key=msg_id, value=event)
            KAFKA_PRODUCED.labels(job=JOB, topic=self.outgoing_topic).inc()

        if failures:
            dlq_event = {"message_id": msg_id, "failures": failures, "original": message, "timestamp": time.time()}
            await self.kafka_client.send(self.dlq_topic, key=msg_id, value=dlq_event)
            KAFKA_PRODUCED.labels(job=JOB, topic=self.dlq_topic).inc()

        duration = time.time() - start_time
        WORKER_PROCESS_SECONDS.labels(job=JOB).observe(duration)

        # cleanup dedup key (policy: allow replays later). Remove this to keep idempotency forever.
        await redis.delete(dedup_key)
