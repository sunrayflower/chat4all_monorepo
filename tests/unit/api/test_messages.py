import pytest
from httpx import AsyncClient
from api_frontend.app.main import app


@pytest.mark.asyncio\async def test_send_message_ok(monkeypatch):
async def mock_kafka_send(topic, key, value):
assert topic == "incoming.messages"
monkeypatch.setattr("api_frontend.app.kafka_producer.kafka_producer.send", mock_kafka_send)


token = "Bearer testtoken"


async with AsyncClient(app=app, base_url="http://test") as ac:
r = await ac.post(
"/v1/messages",
json={
"conversation_id": "conv1",
"sender_id": "u1",
"recipient_ids": ["u2"],
"content": "hello"
},
headers={"Authorization": token}
)
assert r.status_code == 200
assert r.json()["accepted"] is True