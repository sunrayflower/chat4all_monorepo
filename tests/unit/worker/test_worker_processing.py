import pytest
import asyncio
from services.worker.app.consumer import WorkerConsumer


@pytest.mark.asyncio
async def test_worker_delivers(monkeypatch):
calls = []
async def mock_send_to_adapter(*args, **kwargs):
calls.append(True)
return {"ok": True}


monkeypatch.setattr("services.worker.app.adapter_client.AdapterClient.send_to_adapter", mock_send_to_adapter)


# Fake Kafka client
class DummyKafka:
async def send(self, *a, **k): pass


worker = WorkerConsumer(kafka_client=DummyKafka(), http_session=None)
message = {
"message_id": "mid1",
"conversation_id": "c1",
"sender_id": "u1",
"recipient_ids": ["tg_1234"],
"payload_type": "text",
"payload_ref": "hello"
}


await worker._handle_message(message)
assert len(calls) == 1