import requests
import websockets
import asyncio

class ChatClient:
    def __init__(self, api_url, token=None):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}

    def send_message(self, payload: dict):
        r = requests.post(f'{self.api_url}/v1/messages', json=payload, headers=self.headers)
        r.raise_for_status()
        return r.json()

    async def stream_events(self, user_id: str, on_message):
        uri = f'ws://{self.api_url.split("//")[-1]}/v1/ws/{user_id}'
        async with websockets.connect(uri) as ws:
            while True:
                data = await ws.recv()
                on_message(data)
