import uuid
import time
import asyncio
import aiohttp
from .uploader import UploadManager
from .utils import retry_async


class Chat4AllClient:
def __init__(self, base_url: str, token: str, timeout: int = 15):
self.base_url = base_url.rstrip("/")
self.token = token
self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
self.upload = UploadManager(self)


async def close(self):
await self.session.close()


async def send_message(self, conversation_id: str, sender_id: str, recipients: list, content: str, message_id: str=None, metadata: dict=None):
message_id = message_id or str(uuid.uuid4())
url = f"{self.base_url}/v1/messages"
payload = {
"conversation_id": conversation_id,
"sender_id": sender_id,
"recipient_ids": recipients,
"content": content,
"message_id": message_id,
"metadata": metadata or {}
}


async def _do():
async with self.session.post(url, json=payload, headers={"Authorization": f"Bearer {self.token}"}) as r:
if r.status in (200, 201):
return await r.json()
if r.status == 409:
return {"accepted": True, "message_id": message_id, "duplicate": True}
raise Exception(f"send_message failed {r.status}: {await r.text()}")


return await retry_async(_do)