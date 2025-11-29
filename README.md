# Chat4all Prototype Monorepo

This repository contains a minimal, runnable prototype scaffold for Chat4all (Python-first).
It's intended for local development and experimentation, not production.

Services included:
- api_frontend (FastAPI)
- router_worker (Kafka consumer/producer)
- connectors (Telegram adapter skeleton)
- uploader (FastAPI skeleton for multipart uploads)
- sdk (simple Python client)
- docker-compose to run local dependencies (Redpanda, Mongo, MinIO, Redis)

How to run (dev):
1. Install Docker and Docker Compose.
2. From repo root: `docker-compose up --build`
3. Open `http://localhost:8000/docs` for API docs (after api_frontend starts).

Notes:
- This is a starting point. Adapt credentials, hosts, and production configs before use.
