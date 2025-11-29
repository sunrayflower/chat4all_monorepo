import pytest
import aiohttp
from chat4all_sdk.client import Chat4AllClient


@pytest.mark.asyncio\async def test_python_sdk_sends(monkeypatch):
async def fake_post(url, json, headers):
return type("R", (), {"status":200, "json":lambda: {"accepted": True}})


monkeypatch.setattr(aiohttp.ClientSession, "post", fake_post)


client = Chat4AllClient("http://x", "t")
r = await client.send_message(
"c1", "u1", ["u2"], "hello"
)
assert r["accepted"] is True