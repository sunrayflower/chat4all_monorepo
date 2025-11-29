import os
import aiohttp
from .utils import retry_async


class UploadManager:
def __init__(self, client):
self.client = client


async def init_upload(self, owner_id: str, filename: str):
url = f"{self.client.base_url}/v1/uploads/init"


async with self.client.session.post(
url,
params={"owner_id": owner_id, "filename": filename},
headers={"Authorization": f"Bearer {self.client.token}"}
) as r:
if r.status != 200:
raise Exception(f"init_upload failed: {await r.text()}")
return await r.json()


async def upload_file(self, owner_id: str, filepath: str, chunk_size: int = 5 * 1024 * 1024):
meta = await self.init_upload(owner_id, os.path.basename(filepath))
object_key = meta["object_key"]
presigned = meta["presigned_fields"]


url = presigned["url"]
fields = presigned["fields"]


with open(filepath, "rb") as f:
data = f.read()


form = aiohttp.FormData()
for k,v in fields.items():
form.add_field(k, v)
form.add_field("file", data, filename=os.path.basename(filepath))


async def _do():
async with self.client.session.post(url, data=form) as r:
if r.status not in (200,204,201):
raise Exception(f"upload error: {await r.text()}")
return True


await retry_async(_do)
return {"ok": True, "object_key": object_key}