import asyncio


async def retry_async(fn, retries: int = 4, base: float = 0.5):
for attempt in range(retries):
try:
return await fn()
except Exception as e:
if attempt == retries - 1:
raise
await asyncio.sleep(base * (2 ** attempt))