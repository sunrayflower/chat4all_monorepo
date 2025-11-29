import os
import asyncio
from fastapi import FastAPI, Request, Response
from .routes import router
from .kafka_producer import kafka_producer
from .db import init_db, close_db
from .websocket_mgr import ws_manager

# Prometheus client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="chat4all API")

app.include_router(router, prefix="/v1")

# Prometheus metrics
JOB = "api_frontend"
HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "code", "job"])
HTTP_REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency seconds", ["job"])
WS_CONNECTIONS = Counter("api_ws_connections_total", "Active websocket connections", ["job"])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time
    start = time.time()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        raise
    finally:
        duration = time.time() - start
        # label path minimally to avoid high cardinality; for more advanced use replace dynamic segments
        path = request.url.path
        HTTP_REQUESTS.labels(method=request.method, path=path, code=str(status_code), job=JOB).inc()
        HTTP_REQUEST_LATENCY.labels(job=JOB).observe(duration)
    return response

@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint. Prometheus scrapes this.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.on_event("startup")
async def startup():
    os.environ.setdefault("KAFKA_BOOTSTRAP", "redpanda:9092")
    os.environ.setdefault("MONGO_URI", "mongodb://mongo:27017")
    os.environ.setdefault("REDIS_URI", "redis://redis:6379/0")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
    os.environ.setdefault("JWT_SIGNING_KEY", "replace_me_in_prod")

    await init_db()
    await kafka_producer.start()

@app.on_event("shutdown")
async def shutdown():
    await kafka_producer.stop()
    await close_db()
    await ws_manager.close_all()
