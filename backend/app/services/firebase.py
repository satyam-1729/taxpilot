from pathlib import Path

import firebase_admin
from fastapi import HTTPException, status
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from app.core.config import get_settings

_app: firebase_admin.App | None = None


def init_firebase() -> firebase_admin.App:
    global _app
    if _app is not None:
        return _app
    settings = get_settings()
    path = Path(settings.firebase_service_account_path)
    if not path.exists():
        raise RuntimeError(
            f"Firebase service account JSON not found at {path}. "
            "Download it from Firebase Console → Project settings → Service accounts."
        )
    cred = credentials.Certificate(str(path))
    _app = firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id or None})
    return _app


def verify_id_token(id_token: str) -> dict:
    try:
        return fb_auth.verify_id_token(id_token, check_revoked=False)
    except fb_auth.ExpiredIdTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token expired") from e
    except fb_auth.InvalidIdTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token") from e
    except Exception as e:  # firebase_admin can raise various ValueError subclasses
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {e}") from e
