import os
import asyncio
import logging
from aiohttp import web, ClientSession, ClientTimeout
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("instagram_adapter")

IG_API_BASE = "https://graph.facebook.com"
IG_USER_ID = os.getenv("INSTAGRAM_IG_USER_ID", "")
TOKEN = os.getenv("INSTAGRAM_TOKEN", "")
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))
BASE_BACKOFF = float(os.getenv("BASE_BACKOFF", "0.5"))

ADAPTER_REQUESTS = Counter('adapter_requests_total', 'Adapter requests', ['adapter', 'status'])
ADAPTER_LATENCY = Histogram('adapter_request_duration_seconds', 'Adapter latency seconds', ['adapter'])

async def metrics(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)

async def send_text(session: ClientSession, recipient: str, text: str):
    url = f"{IG_API_BASE}/v17.0/{IG_USER_ID}/messages"
    params = {"access_token": TOKEN}
    payload = {
        "recipient": {"id": recipient},
        "message": {"text": text}
    }
    async with session.post(url, params=params, json=payload) as resp:
        txt = await resp.text()
        if resp.status >=200 and resp.status <300:
            return await resp.json()
        raise Exception(f"IG API {resp.status}: {txt}")

async def send_media(session: ClientSession, recipient: str, media_url: str, media_type: str = "image", caption: str = None):
    url = f"{IG_API_BASE}/v17.0/{IG_USER_ID}/messages"
    params = {"access_token": TOKEN}
    attachment = {}
    if media_type == "image":
        attachment = {"type":"image", "payload":{"url": media_url}}
    elif media_type == "video":
        attachment = {"type":"video", "payload":{"url": media_url}}
    else:
        attachment = {"type":"file", "payload":{"url": media_url}}
    payload = {"recipient": {"id": recipient}, "message": {"attachment": attachment}}
    if caption:
        payload["message"]["text"] = caption
    async with session.post(url, params=params, json=payload) as resp:
        txt = await resp.text()
        if resp.status >=200 and resp.status <300:
            return await resp.json()
        raise Exception(f"IG API {resp.status}: {txt}")

async def do_with_retries(fn, *args, **kwargs):
    attempt = 0
    while True:
        start = asyncio.get_event_loop().time()
        try:
            res = await fn(*args, **kwargs)
            ADAPTER_REQUESTS.labels(adapter='instagram', status='success').inc()
            ADAPTER_LATENCY.labels(adapter='instagram').observe(asyncio.get_event_loop().time() - start)
            return res
        except Exception as e:
            attempt += 1
            ADAPTER_REQUESTS.labels(adapter='instagram', status='error').inc()
            if attempt > MAX_RETRIES:
                log.exception("max retries reached")
                raise
            backoff = BASE_BACKOFF * (2 ** (attempt - 1))
            log.warning("attempt %s failed, sleeping %s: %s", attempt, backoff, e)
            await asyncio.sleep(backoff)

async def handle_send(request):
    data = await request.json()
    message = data.get("message", {})
    recipient = data.get("recipient_id")
    if not recipient:
        return web.json_response({"error":"missing recipient_id"}, status=400)

    ptype = message.get("payload_type","text")
    pref = message.get("payload_ref")
    try:
        async with ClientSession(timeout=ClientTimeout(total=TIMEOUT)) as s:
            if ptype == "text" or isinstance(pref, str):
                text = pref if isinstance(pref, str) else message.get("payload_ref","")
                res = await do_with_retries(send_text, s, recipient, text)
            elif ptype in ("image","video","file"):
                info = pref or {}
                url = info.get("url")
                mime = info.get("mime")
                caption = info.get("caption")
                if not url:
                    return web.json_response({"error":"missing media url"}, status=400)
                mtype = "image" if (mime and mime.startswith("image/")) else ("video" if (mime and mime.startswith("video/")) else "file")
                res = await do_with_retries(send_media, s, recipient, url, mtype, caption)
            else:
                return web.json_response({"error":"unsupported payload_type"}, status=400)
    except Exception as e:
        log.exception("instagram send failed")
        return web.json_response({"error":str(e)}, status=502)
    return web.json_response({"status":"ok","provider_response":res})

app = web.Application()
app.router.add_post("/send", handle_send)
app.router.add_get("/metrics", metrics)

if __name__ == "__main__":
    port = int(os.getenv("PORT","8003"))
    web.run_app(app, host="0.0.0.0", port=port)

