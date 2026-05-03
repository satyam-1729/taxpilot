from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_session_token, current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import KycRequest, SessionRequest, SessionResponse, UserOut
from app.services.firebase import verify_id_token
from app.services.redis_client import incr_with_ttl
from app.utils.crypto import encrypt_field

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session", response_model=SessionResponse)
async def create_session(body: SessionRequest, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Exchange a Firebase ID token for our session JWT. Upserts the user row."""
    claims = verify_id_token(body.id_token)
    firebase_uid: str = claims["uid"]

    # Basic per-UID rate limit on session creation (prevents token replay floods)
    count = await incr_with_ttl(f"rl:session:{firebase_uid}", ttl_seconds=60)
    if count > 20:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many session requests")

    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()
    now = datetime.now(tz=timezone.utc)

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            phone=claims.get("phone_number"),
            email=claims.get("email"),
            name=claims.get("name"),
            last_login_at=now,
        )
        db.add(user)
    else:
        # Refresh profile fields that may have changed in Firebase
        user.phone = claims.get("phone_number") or user.phone
        user.email = claims.get("email") or user.email
        user.name = claims.get("name") or user.name
        user.last_login_at = now

    await db.commit()
    await db.refresh(user)

    token = create_session_token(user.id)
    return SessionResponse(token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/kyc", response_model=UserOut)
async def complete_kyc(
    body: KycRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if user.verified:
        return UserOut.model_validate(user)

    user.name = body.name
    user.dob = body.dob
    user.pan_encrypted = encrypt_field(body.pan)
    user.pan_last4 = body.pan[-4:]
    user.aadhaar_last4 = body.aadhaar[-4:]
    user.verified = True
    user.verified_at = datetime.now(tz=timezone.utc)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(current_user)) -> None:
    # Stateless JWT — client discards the token. Hook here if we move to a session-id store.
    return None
