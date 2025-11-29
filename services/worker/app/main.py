import asyncio
import os
from .consumer import WorkerConsumer
from .kafka_client import KafkaClient
from .db import init_db, close_db
from aiohttp import ClientSession, web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

# Prometheus metrics helpers for worker (counters/histogram)
JOB = "worker"
KAFKA_CONSUMED = Counter('kafka_consumed_messages_total', 'Consumed Kafka messages', ['job'])
KAFKA_PRODUCED = Counter('kafka_produced_messages_total', 'Produced Kafka messages', ['job','topic'])
WORKER_PROCESS_SECONDS = Histogram('worker_process_seconds', 'Worker processing time', ['job'])
DEDUP_HITS = Counter('redis_dedup_hits_total', 'Dedup hits (redis)', ['job'])

worker = None
kafka_client = None
http_session = None

async def metrics_handler(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)

async def startup():
    global worker, kafka_client, http_session
    os.environ.setdefault("KAFKA_BOOTSTRAP", "redpanda:9092")
    os.environ.setdefault("MONGO_URI", "mongodb://mongo:27017")
    os.environ.setdefault("REDIS_URI", "redis://redis:6379/0")

    await init_db()
    kafka_client = KafkaClient()
    await kafka_client.start()
    http_session = ClientSession()
    # pass metric objects into WorkerConsumer via environment or direct import; our consumer imports same names
    worker = WorkerConsumer(kafka_client=kafka_client, http_session=http_session)
    await worker.start()

    # start a small aiohttp server to expose /metrics
    metrics_app = web.Application()
    metrics_app.router.add_get('/metrics', metrics_handler)
    runner = web.AppRunner(metrics_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("WORKER_METRICS_PORT", "8000")))
    await site.start()
    print("Worker metrics server started on port", os.getenv("WORKER_METRICS_PORT", "8000"))

async def shutdown():
    global worker, kafka_client, http_session
    if worker:
        await worker.stop()
    if kafka_client:
        await kafka_client.stop()
    if http_session:
        await http_session.close()
    await close_db()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(startup())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(shutdown())
