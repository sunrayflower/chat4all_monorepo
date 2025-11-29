import pytest
from aiohttp import web
from services.adapters.whatsapp_cloud.app import app


@pytest.mark.asyncio
async def test_whatsapp_adapter_mock(aiohttp_client):
client = await aiohttp_client(app)
r = await client.post("/send", json={
"message": {"payload_type": "text", "payload_ref": "hello"},
"recipient_id": "5511999"
})
assert r.status == 200