import asyncio
import aiohttp
import json
from typing import Optional

# Adapter contract:
# Each adapter is an HTTP service with POST /send that accepts JSON:
# { "message": {...}, "recipient_id": "..." }
# and returns 200 on success, 4xx/5xx on failure.

class AdapterError(Exception):
    pass

class AdapterClient:
    def __init__(self, http_session: aiohttp.ClientSession, timeout=10):
        self.session = http_session
        self.timeout = timeout
        # resolver map can be env-driven; default examples:
        # map 'whatsapp' -> http://connector_whatsapp:8000
        self.adapter_map = {
            "whatsapp": lambda rid: f"http://connector_whatsapp:8000",
            "telegram": lambda rid: f"http://connector_telegram:8000",
            "instagram": lambda rid: f"http://connector_instagram:8000",
            "default": lambda rid: f"http://connector_mock:8000"
        }

    def resolve_adapter_base(self, channel_hint: Optional[str], recipient_id: str):
        if channel_hint and channel_hint in self.adapter_map:
            return self.adapter_map[channel_hint](recipient_id)
        # simple resolver: if recipient prefix matches
        if recipient_id.startswith("wa_"):
            return self.adapter_map["whatsapp"](recipient_id)
        if recipient_id.startswith("tg_"):
            return self.adapter_map["telegram"](recipient_id)
        if recipient_id.startswith("ig_"):
            return self.adapter_map["instagram"](recipient_id)
        return self.adapter_map["default"](recipient_id)

    async def send_to_adapter(self, url_base: str, message: dict, recipient_id: str, timeout_override: int = None):
        url = f"{url_base.rstrip('/')}/send"
        payload = {"message": message, "recipient_id": recipient_id}
        timeout = aiohttp.ClientTimeout(total=timeout_override or self.timeout)
        async with self.session.post(url, json=payload, timeout=timeout) as resp:
            text = await resp.text()
            if resp.status >= 200 and resp.status < 300:
                try:
                    return await resp.json()
                except:
                    return {"status": "ok", "raw": text}
            else:
                raise AdapterError(f"Adapter returned {resp.status}: {text}")
