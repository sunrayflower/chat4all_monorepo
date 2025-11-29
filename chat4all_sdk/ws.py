import asyncio
import websockets


class WSClient:
def __init__(self, base_url: str, user_id: str):
self.url = base_url.replace("http", "ws") + f"/v1/ws/{user_id}"
self.ws = None


async def connect(self):
self.ws = await websockets.connect(self.url)
return self


async def listen(self, callback):
async for msg in self.ws:
callback(msg)


async def close(self):
if self.ws:
await self.ws.close()