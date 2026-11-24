"""
Authentication for AEGIS.

* Google Sign-In: the React app gets a Google OAuth access token (Google Identity Services
  popup) and posts it here. We verify the token's audience against GOOGLE_CLIENT_ID via
  Google's tokeninfo endpoint, then read the profile from the userinfo endpoint.
* Local profile: when no GOOGLE_CLIENT_ID is configured (or Google is unreachable) the user
  can create a local profile so the demo still works fully offline.

Sessions are stateless HMAC-signed tokens (stdlib only, no extra dependency).
"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.database import SessionLocal
from backend.models import User

logger = logging.getLogger("AEGIS.Auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"


# --------------------------------------------------------------------------- tokens
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int, ttl_hours: Optional[int] = None) -> str:
    ttl = (ttl_hours if ttl_hours is not None else settings.AUTH_TOKEN_TTL_HOURS) * 3600
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(settings.AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_token(token: str) -> Optional[int]:
    """Returns the user id for a valid, unexpired token, otherwise None."""
    try:
        payload, sig = token.split(".", 1)
        expected = _b64(hmac.new(settings.AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except Exception:
        return None


# --------------------------------------------------------------------------- google
async def _fetch_json(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise ValueError(f"{url} returned {resp.status_code}")
    return resp.json()


async def verify_google_access_token(access_token: str) -> Dict[str, Any]:
    """Validate a Google OAuth access token for *this* app and return the user's profile."""
    if not settings.GOOGLE_CLIENT_ID:
        raise ValueError("Google sign-in is not configured (GOOGLE_CLIENT_ID is empty).")
    info = await _fetch_json(GOOGLE_TOKENINFO, params={"access_token": access_token})
    audience = info.get("aud") or info.get("azp")
    if audience != settings.GOOGLE_CLIENT_ID:
        raise ValueError("Token was not issued for this application.")
    profile = await _fetch_json(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access_token}"})
    if not profile.get("sub"):
        raise ValueError("Google profile is missing a subject id.")
    return profile


# --------------------------------------------------------------------------- users
def user_to_dict(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "provider": u.provider,
        "email": u.email,
        "name": u.name,
        "picture": u.picture,
        "role": u.role or "",
        "initial": (u.name or "?").strip()[:1].upper(),
    }


def upsert_user(provider: str, subject: str, name: str, email: str = "", picture: str = "", role: Optional[str] = None) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.provider == provider, User.subject == subject).first()
        now = datetime.datetime.utcnow()
        if user:
            user.name = name or user.name
            user.email = email or user.email
            user.picture = picture or user.picture
            if role:
                user.role = role
            user.last_login = now
        else:
            user = User(provider=provider, subject=subject, name=name, email=email,
                        picture=picture, role=role or "", last_login=now)
            db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_dict(user)
    finally:
        db.close()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        return user_to_dict(u) if u else None
    finally:
        db.close()


def _current_user(authorization: Optional[str]) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    uid = verify_token(authorization.split(" ", 1)[1].strip())
    user = get_user(uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


# --------------------------------------------------------------------------- routes
class GoogleLogin(BaseModel):
    access_token: str


class LocalLogin(BaseModel):
    name: str
    role: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


@router.get("/config")
async def auth_config():
    return {"google_enabled": bool(settings.GOOGLE_CLIENT_ID), "google_client_id": settings.GOOGLE_CLIENT_ID}


@router.post("/google")
async def login_google(body: GoogleLogin):
    try:
        profile = await verify_google_access_token(body.access_token)
    except Exception as e:
        logger.warning(f"Google sign-in rejected: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    user = upsert_user("google", profile["sub"], profile.get("name", ""), profile.get("email", ""), profile.get("picture", ""))
    return {"token": create_token(user["id"]), "user": user}


@router.post("/local")
async def login_local(body: LocalLogin):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    user = upsert_user("local", name.lower(), name, role=(body.role or "").strip() or None)
    return {"token": create_token(user["id"]), "user": user}


@router.get("/me")
async def me(authorization: Optional[str] = Header(None)):
    return {"user": _current_user(authorization)}


@router.patch("/profile")
async def update_profile(body: ProfileUpdate, authorization: Optional[str] = Header(None)):
    user = _current_user(authorization)
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.id == user["id"]).first()
        if body.name and body.name.strip():
            row.name = body.name.strip()
        if body.role is not None:
            row.role = body.role.strip()
        db.commit()
        db.refresh(row)
        return {"user": user_to_dict(row)}
    finally:
        db.close()
