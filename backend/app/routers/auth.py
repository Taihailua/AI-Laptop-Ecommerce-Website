from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
import bcrypt

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str


def require_admin_token(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> str:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_admin_token:
        token = x_admin_token.strip()

    if token != "mock-token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required")

    return token

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Tài khoản không tồn tại")
    
    # Check password
    try:
        # DB stores hash string like $2b$12$...
        # bcrypt.checkpw needs bytes for both
        valid = bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8'))
    except Exception as e:
        print(f"Auth Error: {e}")
        valid = False

    if not valid:
        raise HTTPException(status_code=400, detail="Mật khẩu không đúng")
        
    return {"message": "Login successful", "token": "mock-token", "role": user.role}