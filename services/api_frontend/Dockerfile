FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y gcc libpq-dev build-essential \
  && pip install --no-cache-dir fastapi uvicorn[standard] aiokafka motor aioredis pydantic boto3 pyjwt botocore

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
