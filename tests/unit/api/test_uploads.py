import pytest
from httpx import AsyncClient
from api_frontend.app.main import app


@pytest.mark.asyncio\async def test_init_upload(monkeypatch):
class MockS3:
def generate_presigned_post(self, **kwargs):
return {"url": "http://minio/upload", "fields": {}}


monkeypatch.setattr("boto3.client", lambda *a, **k: MockS3())


async with AsyncClient(app=app, base_url="http://test") as ac:
r = await ac.post("/v1/uploads/init?owner_id=u1&filename=a.png")
assert r.status_code == 200
assert "object_key" in r.json()