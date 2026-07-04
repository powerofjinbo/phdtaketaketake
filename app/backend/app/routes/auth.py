from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_user, hash_password, verify_password
from ..db import get_db
from ..models import User

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/register")
def register(body: Credentials, db: Session = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"access_token": create_token(user.id)}


@router.post("/auth/guest")
def guest(db: Session = Depends(get_db)):
    """No-signup access: mint an anonymous account. The token in the
    client's localStorage IS the identity — losing it loses the data,
    which is the honest trade-off of guest mode."""
    import secrets

    email = f"guest-{secrets.token_hex(8)}@guest.phdtake"
    user = User(email=email, password_hash=hash_password(secrets.token_hex(16)))
    db.add(user)
    db.commit()
    return {"access_token": create_token(user.id), "guest": True}


@router.post("/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user.id)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "guest": user.email.endswith("@guest.phdtake")}
