import os
import asyncio
import logging
from aiohttp import web, ClientSession, ClientTimeout
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram_adapter")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))
BASE_BACKOFF = float(os.getenv("BASE_BACKOFF", "0.3"))

ADAPTER_REQUESTS = Counter('adapter_requests_total', 'Adapter requests', ['adapter', 'status'])
ADAPTER_LATENCY = Histogram('adapter_request_duration_seconds', 'Adapter latency seconds', ['adapter'])

async def metrics(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)

async def send_text(session: ClientSession, chat_id: str, text: str):
    url = f"{API_BASE}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    async with session.post(url, json=payload) as resp:
        txt = await resp.text()
        if resp.status >=200 and resp.status <300:
            return await resp.json()
        raise Exception(f"Telegram API {resp.status}: {txt}")

async def send_photo(session: ClientSession, chat_id: str, photo_url: str, caption: str = None):
    url = f"{API_BASE}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    async with session.post(url, json=payload) as resp:
        txt = await resp.text()
        if resp.status >=200 and resp.status <300:
            return await resp.json()
        raise Exception(f"Telegram API {resp.status}: {txt}")

async def do_with_retries(fn, *args, **kwargs):
    attempt = 0
    while True:
        start = asyncio.get_event_loop().time()
        try:
            res = await fn(*args, **kwargs)
            ADAPTER_REQUESTS.labels(adapter='telegram', status='success').inc()
            ADAPTER_LATENCY.labels(adapter='telegram').observe(asyncio.get_event_loop().time() - start)
            return res
        except Exception as e:
            attempt += 1
            ADAPTER_REQUESTS.labels(adapter='telegram', status='error').inc()
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
        return web.json_response({"error": "missing recipient_id"}, status=400)
    chat_id = recipient.replace("tg_", "") if recipient.startswith("tg_") else recipient

    ptype = message.get("payload_type", "text")
    pref = message.get("payload_ref")
    try:
        async with ClientSession(timeout=ClientTimeout(total=TIMEOUT)) as s:
            if ptype == "text" or isinstance(pref, str):
                text = pref if isinstance(pref, str) else message.get("payload_ref", "")
                res = await do_with_retries(send_text, s, chat_id, text)
            elif ptype in ("image","photo"):
                info = pref or {}
                url = info.get("url")
                caption = info.get("caption")
                if not url:
                    return web.json_response({"error":"missing image url"}, status=400)
                res = await do_with_retries(send_photo, s, chat_id, url, caption)
            else:
                return web.json_response({"error":"unsupported payload_type"}, status=400)
    except Exception as e:
        log.exception("telegram send failed")
        return web.json_response({"error": str(e)}, status=502)
    return web.json_response({"status":"ok","provider_response":res})

app = web.Application()
app.router.add_post("/send", handle_send)
app.router.add_get("/metrics", metrics)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    web.run_app(app, host="0.0.0.0", port=port)
