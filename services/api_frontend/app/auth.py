import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

_signing_key = os.getenv("JWT_SIGNING_KEY", "replace_me_in_prod")
_algo = "HS256"
bearer = HTTPBearer(auto_error=False)

class TokenData(BaseModel):
    sub: str

def create_jwt(subject: str, expires_minutes: int = 60*24):
    payload = {
        "sub": subject,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, _signing_key, algorithm=_algo)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth")
    token = credentials.credentials
    try:
        data = jwt.decode(token, _signing_key, algorithms=[_algo])
        return data.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
