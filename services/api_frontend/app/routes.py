import os, uuid, time, asyncio
from fastapi import APIRouter, WebSocket, Depends, HTTPException, UploadFile, BackgroundTasks
from .models import SendMessageReq, SendMessageResp, InitUploadResp, HealthResp
from .auth import get_current_user, create_jwt
from .db import messages_collection, file_uploads_collection, redis
from .kafka_producer import kafka_producer
from .websocket_mgr import ws_manager
import boto3
from botocore.client import Config

router = APIRouter()

# Health
@router.get("/health", response_model=HealthResp)
async def health():
    return {"ok": True}

# simple token generator for dev/testing (not for prod!)
@router.post("/auth/token")
def token_for(user_id: str):
    token = create_jwt(user_id)
    return {"access_token": token}

# send message
@router.post("/messages", response_model=SendMessageResp)
async def send_message(req: SendMessageReq, user: str = Depends(get_current_user)):
    mid = req.message_id or str(uuid.uuid4())
    message = {
        "message_id": mid,
        "conversation_id": req.conversation_id,
        "sender_id": req.sender_id,
        "recipient_ids": req.recipient_ids,
        "channel_hint": None,
        "payload_type": "text",
        "payload_ref": req.content,
        "metadata": req.metadata or {},
        "created_at": time.time(),
    }
    # dedup: set NX with TTL
    dedup_key = f"dedup:{mid}"
    existed = await redis.set(dedup_key, "1", ex=60*60, nx=True)
    if not existed:
        # existed == False means key already there -> duplicate
        raise HTTPException(status_code=409, detail="Duplicate message_id")

    # persist minimal metadata
    await messages_collection.insert_one({**message, "state": "SENT"})

    # push to Kafka incoming.messages
    await kafka_producer.send("incoming.messages", message["conversation_id"], message)

    # optionally notify connected websocket recipients
    for rid in req.recipient_ids:
        await ws_manager.send_personal(rid, f"[new_message] {mid}")

    return {"accepted": True, "message_id": mid}

# websocket endpoint for clients to receive events
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id: str):
    await ws_manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            # echo for now
            await ws.send_text(f"echo: {data}")
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(user_id, ws)

# presigned multipart/init (MinIO/S3)
@router.post("/uploads/init", response_model=InitUploadResp)
async def init_upload(owner_id: str, filename: str, user: str = Depends(get_current_user)):
    upload_id = str(uuid.uuid4())
    key = f"{owner_id}/{upload_id}/{filename}"

    s3_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket = os.getenv("MINIO_BUCKET", "chat4all")

    # ensure bucket exists (sync boto)
    s3 = boto3.client(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        try:
            s3.create_bucket(Bucket=bucket)
        except Exception:
            pass

    # presigned post for browser/multipart part upload (for simple flow)
    presigned = s3.generate_presigned_post(Bucket=bucket, Key=key, ExpiresIn=3600)

    # store control doc
    await file_uploads_collection.insert_one({
        "upload_id": upload_id,
        "owner_user_id": owner_id,
        "object_key": key,
        "status": "IN_PROGRESS",
        "created_at": time.time()
    })

    return {"upload_id": upload_id, "object_key": key, "presigned_fields": presigned}

# endpoint to publish an event to a websocket user (admin/testing)
@router.post("/ws/publish")
async def publish_ws(user_id: str, message: str, user: str = Depends(get_current_user)):
    await ws_manager.send_personal(user_id, message)
    return {"ok": True}

