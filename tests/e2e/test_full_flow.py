import pytest
import time
import httpx


@pytest.mark.asyncio
async def test_full_chain():
# 1. send message
async with httpx.AsyncClient() as ac:
r = await ac.post("http://localhost:8000/v1/messages", json={
"conversation_id": "c1",
"sender_id": "alice",
"recipient_ids": ["tg_123"],
"content": "hello"
})
assert r.status_code == 200
msg_id = r.json()["message_id"]


# 2. allow worker to process
time.sleep(3)


# 3. verify message in mongo
import pymongo
db = pymongo.MongoClient("localhost", 27017).chat4all
doc = db.messages.find_one({"message_id": msg_id})
assert doc is not None
assert doc["state"] in ("DELIVERED", "PARTIAL")