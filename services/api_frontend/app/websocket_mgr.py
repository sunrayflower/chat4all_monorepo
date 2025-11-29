from fastapi import WebSocket
from typing import Dict, Set
import asyncio

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.connections.setdefault(user_id, set()).add(ws)

    async def disconnect(self, user_id: str, ws: WebSocket):
        async with self.lock:
            conns = self.connections.get(user_id)
            if conns and ws in conns:
                conns.remove(ws)
                if not conns:
                    self.connections.pop(user_id, None)

    async def send_personal(self, user_id: str, message: str):
        conns = self.connections.get(user_id, set()).copy()
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                await self.disconnect(user_id, ws)

    async def broadcast(self, message: str):
        # naive broadcast
        keys = list(self.connections.keys())
        for k in keys:
            await self.send_personal(k, message)

    async def close_all(self):
        for conns in list(self.connections.values()):
            for ws in list(conns):
                try:
                    await ws.close()
                except:
                    pass
        self.connections.clear()

ws_manager = WebSocketManager()
