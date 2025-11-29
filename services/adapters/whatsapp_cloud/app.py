# simple aiohttp adapter for WhatsApp Cloud API with metrics
import os
import asyncio
import logging
from aiohttp import web, ClientSession, ClientTimeout
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("whatsapp_adapter")

WA_API_BASE = "https://graph.facebook.com"
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
TOKEN = os.getenv("WHATSAPP_TOKEN", "")
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))
BASE_BACKOFF = float(os.getenv("BASE_BACKOFF", "0.5"))

# Prometheus metrics
ADAPTER_REQUESTS = Counter('adapter_requests_total', 'Adapter requests', ['adapter', 'status'])
ADAPTER_LATENCY = Histogram('adapter_request_duration_seconds', 'Adapter latency seconds', ['adapter'])

async def metrics(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)

async def forward_text(session: ClientSession, recipient: str, text: str):
    url = f"{WA_API_BASE}/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }
    async with session.post(url, json=payload, headers=headers) as resp:
        text_resp = await resp.text()
        if resp.status >= 200 and resp.status < 300:
            return await resp.json()
        raise web.HTTPBadGateway(text=f"WA API error {resp.status}: {text_resp}")

async def forward_media(session: ClientSession, recipient: str, media_url: str, mime: str = None, caption: str = None):
    url = f"{WA_API_BASE}/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    t = "document"
    if mime and mime.startswith("image/"):
        t = "image"
    elif mime and mime.startswith("video/"):
        t = "video"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": t,
        t: {"link": media_url}
    }
    if caption and t == "image":
        payload["image"]["caption"] = caption
    async with session.post(url, json=payload, headers=headers) as resp:
        text_resp = await resp.text()
        if resp.status >= 200 and resp.status < 300:
            return await resp.json()
        raise web.HTTPBadGateway(text=f"WA API error {resp.status}: {text_resp}")

async def do_with_retries(fn, *args, **kwargs):
    attempt = 0
    while True:
        start = asyncio.get_event_loop().time()
        try:
            res = await fn(*args, **kwargs)
            ADAPTER_REQUESTS.labels(adapter='whatsapp', status='success').inc()
            ADAPTER_LATENCY.labels(adapter='whatsapp').observe(asyncio.get_event_loop().time() - start)
            return res
        except Exception as e:
            attempt += 1
            ADAPTER_REQUESTS.labels(adapter='whatsapp', status='error').inc()
            if attempt > MAX_RETRIES:
                log.exception("max retries reached")
                raise
            backoff = BASE_BACKOFF * (2 ** (attempt - 1))
            log.warning("attempt %s failed, backing off %s: %s", attempt, backoff, e)
            await asyncio.sleep(backoff)

async def handle_send(request):
    data = await request.json()
    message = data.get("message", {})
    recipient = data.get("recipient_id")
    if not recipient:
        return web.json_response({"error": "missing recipient_id"}, status=400)

    if recipient.startswith("whatsapp:"):
        r = recipient.split(":", 1)[1]
    else:
        r = recipient

    ptype = message.get("payload_type", "text")
    pref = message.get("payload_ref")
    try:
        async with ClientSession(timeout=ClientTimeout(total=TIMEOUT)) as session:
            if ptype == "text" or isinstance(pref, str):
                text = pref if isinstance(pref, str) else message.get("payload_ref", "")
                res = await do_with_retries(forward_text, session, r, text)
            elif ptype in ("image", "video", "document", "file"):
                info = pref or {}
                media_url = info.get("url")
                mime = info.get("mime")
                caption = info.get("caption")
                if not media_url:
                    return web.json_response({"error": "missing media url"}, status=400)
                res = await do_with_retries(forward_media, session, r, media_url, mime, caption)
            else:
                return web.json_response({"error": "unsupported payload_type"}, status=400)
    except Exception as e:
        log.exception("send failed")
        return web.json_response({"error": str(e)}, status=502)
    return web.json_response({"status": "ok", "provider_response": res})

app = web.Application()
app.router.add_post("/send", handle_send)
app.router.add_get("/metrics", metrics)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    web.run_app(app, host="0.0.0.0", port=port)
