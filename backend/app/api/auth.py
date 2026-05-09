from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_session_token, current_user, get_user_dek
from app.db.session import get_db
from app.models import User
from app.schemas.auth import KycRequest, SessionRequest, SessionResponse, UserOut, user_out_from
from app.services.firebase import verify_id_token
from app.services.redis_client import incr_with_ttl
from app.utils.crypto import (
    blind_index,
    encrypt_date,
    encrypt_str,
    generate_dek,
    unwrap_dek,
    wrap_dek,
)

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

    phone = claims.get("phone_number")
    email = claims.get("email")
    name = claims.get("name")

    if user is None:
        # New user: mint a fresh DEK, wrap it, store only ciphertext + indexes.
        dek = generate_dek()
        user = User(
            firebase_uid=firebase_uid,
            last_login_at=now,
            dek_wrapped=wrap_dek(dek),
            email_ct=encrypt_str(dek, email),
            email_bidx=blind_index(email),
            phone_ct=encrypt_str(dek, phone),
            phone_bidx=blind_index(phone),
            name_ct=encrypt_str(dek, name),
        )
        db.add(user)
    else:
        # Existing user: refresh ciphertext mirrors with whatever Firebase has now.
        dek = unwrap_dek(user.dek_wrapped)
        user.last_login_at = now
        if email:
            user.email_ct = encrypt_str(dek, email)
            user.email_bidx = blind_index(email)
        if phone:
            user.phone_ct = encrypt_str(dek, phone)
            user.phone_bidx = blind_index(phone)
        if name:
            user.name_ct = encrypt_str(dek, name)

    await db.commit()
    await db.refresh(user)

    token = create_session_token(user.id)
    return SessionResponse(token=token, user=user_out_from(user, dek))


@router.get("/me", response_model=UserOut)
async def me(request: Request, user: User = Depends(current_user)) -> UserOut:
    return user_out_from(user, get_user_dek(request, user))


@router.post("/kyc", response_model=UserOut)
async def complete_kyc(
    body: KycRequest,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    dek = get_user_dek(request, user)
    if user.verified:
        return user_out_from(user, dek)

    if dek is None:
        raise HTTPException(status_code=500, detail="User has no DEK; cannot store PII.")

    user.name_ct = encrypt_str(dek, body.name)
    user.dob_ct = encrypt_date(dek, body.dob)
    user.pan_ct = encrypt_str(dek, body.pan)
    user.aadhaar_ct = encrypt_str(dek, body.aadhaar)
    user.pan_last4 = body.pan[-4:]
    user.aadhaar_last4 = body.aadhaar[-4:]
    user.verified = True
    user.verified_at = datetime.now(tz=timezone.utc)

    await db.commit()
    await db.refresh(user)
    return user_out_from(user, dek)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(current_user)) -> None:
    # Stateless JWT — client discards the token. Hook here if we move to a session-id store.
    return None
