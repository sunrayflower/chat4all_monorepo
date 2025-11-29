FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y gcc build-essential \
  && pip install --no-cache-dir -U pip

RUN pip install --no-cache-dir aiokafka aiohttp motor aioredis

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-u", "app/main.py"]

