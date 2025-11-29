from fastapi import FastAPI
import boto3, uuid, os
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()
s3 = boto3.client('s3', endpoint_url=os.getenv('MINIO_ENDPOINT','http://minio:9000'), aws_access_key_id=os.getenv('MINIO_ACCESS','minioadmin'), aws_secret_access_key=os.getenv('MINIO_SECRET','minioadmin'))
BUCKET='chat4all'
client = AsyncIOMotorClient(os.getenv('MONGO_URI','mongodb://mongo:27017'))
file_uploads_collection = client.chat4all.file_uploads

@app.post('/uploads/init')
async def init_upload(owner_id: str, filename: str):
    upload_id = str(uuid.uuid4())
    key = f'{owner_id}/{upload_id}/{filename}'
    resp = s3.create_multipart_upload(Bucket=BUCKET, Key=key)
    await file_uploads_collection.insert_one({'upload_id': upload_id, 'owner_user_id': owner_id, 'object_key': key, 'status':'IN_PROGRESS'})
    return {'upload_id': upload_id, 's3_upload_id': resp.get('UploadId'), 'object_key': key}
