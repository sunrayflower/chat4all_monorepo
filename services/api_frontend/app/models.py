from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SendMessageReq(BaseModel):
    conversation_id: str = Field(..., example="conv:alice:bob")
    sender_id: str
    recipient_ids: List[str]
    content: str
    message_id: Optional[str] = None
    metadata: Optional[Dict[str,Any]] = {}

class SendMessageResp(BaseModel):
    accepted: bool
    message_id: str

class InitUploadResp(BaseModel):
    upload_id: str
    object_key: str
    presigned_fields: dict

class HealthResp(BaseModel):
    ok: bool
