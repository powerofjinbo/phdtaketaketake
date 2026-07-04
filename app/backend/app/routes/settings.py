from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..crypto import encrypt
from ..db import get_db
from ..models import User, UserSettings
from ..providers import PROVIDERS

router = APIRouter()


class SettingsUpdate(BaseModel):
    provider: str
    model: str | None = Field(default=None, max_length=128)
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, max_length=512)


@router.get("/settings")
def get_settings(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    s = db.get(UserSettings, user.id)
    if s is None:
        return {"provider": "anthropic", "model": None, "base_url": None, "has_key": False}
    return {
        "provider": s.provider,
        "model": s.model,
        "base_url": s.base_url,
        "has_key": bool(s.api_key_encrypted),
    }


@router.put("/settings")
def put_settings(
    body: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.provider not in PROVIDERS:
        raise HTTPException(422, f"provider must be one of {PROVIDERS}")
    if body.provider == "custom" and not (body.base_url or "").startswith("http"):
        raise HTTPException(422, "custom provider requires a base_url")
    s = db.get(UserSettings, user.id)
    if s is None:
        s = UserSettings(user_id=user.id)
        db.add(s)
    s.provider = body.provider
    s.model = body.model or None
    s.base_url = body.base_url or None
    if body.api_key:
        s.api_key_encrypted = encrypt(body.api_key.strip())
    db.commit()
    return {"ok": True}
