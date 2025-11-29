import os
from motor.motor_asyncio import AsyncIOMotorClient
import aioredis

mongo_client = None
db = None
messages_collection = None
file_uploads_collection = None
redis = None

async def init_db():
    global mongo_client, db, messages_collection, file_uploads_collection, redis
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_client = AsyncIOMotorClient(mongo_uri)
    db = mongo_client.chat4all
    messages_collection = db.messages
    file_uploads_collection = db.file_uploads

    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    redis = await aioredis.from_url(redis_uri, encoding="utf-8", decode_responses=True)

async def close_db():
    global mongo_client, redis
    if mongo_client:
        mongo_client.close()
    if redis:
        await redis.close()
