from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_session_token, current_user, get_user_dek
from app.db.session import get_db
from app.models import User
from app.schemas.auth import KycRequest, SessionRequest, SessionResponse, UserOut
from app.services.firebase import verify_id_token
from app.services.redis_client import incr_with_ttl
from app.utils.crypto import (
    blind_index,
    encrypt_date,
    encrypt_field,
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
        # New user: mint a fresh DEK, wrap it, encrypt PII alongside plaintext.
        dek = generate_dek()
        user = User(
            firebase_uid=firebase_uid,
            phone=phone,
            email=email,
            name=name,
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
        # Existing user: refresh plaintext fields (Firebase may have updated
        # them) and dual-write the encrypted mirrors. Pre-envelope users get
        # a freshly minted DEK on next login — backfill of any old PAN/Aadhaar
        # rows is left for the data-migration script.
        user.phone = phone or user.phone
        user.email = email or user.email
        user.name = name or user.name
        user.last_login_at = now
        if user.dek_wrapped is None:
            dek = generate_dek()
            user.dek_wrapped = wrap_dek(dek)
        else:
            dek = unwrap_dek(user.dek_wrapped)
        user.email_ct = encrypt_str(dek, user.email)
        user.email_bidx = blind_index(user.email)
        user.phone_ct = encrypt_str(dek, user.phone)
        user.phone_bidx = blind_index(user.phone)
        user.name_ct = encrypt_str(dek, user.name)

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
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if user.verified:
        return UserOut.model_validate(user)

    user.name = body.name
    user.dob = body.dob
    # Legacy KEK-only Fernet path (kept until backfill drops it).
    user.pan_encrypted = encrypt_field(body.pan)
    user.pan_last4 = body.pan[-4:]
    user.aadhaar_last4 = body.aadhaar[-4:]

    # Envelope encryption mirror: encrypt with the user's DEK so a DB-only
    # attacker can't decrypt without also having the server KEK.
    dek = get_user_dek(request, user)
    if dek is not None:
        user.name_ct = encrypt_str(dek, body.name)
        user.dob_ct = encrypt_date(dek, body.dob)
        user.pan_ct = encrypt_str(dek, body.pan)
        user.aadhaar_ct = encrypt_str(dek, body.aadhaar)

    user.verified = True
    user.verified_at = datetime.now(tz=timezone.utc)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(current_user)) -> None:
    # Stateless JWT — client discards the token. Hook here if we move to a session-id store.
    return None
