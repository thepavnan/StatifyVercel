import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from itsdangerous import URLSafeSerializer

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, StatusResponse
from app.services.spotify import spotify_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
signer = URLSafeSerializer(settings.secret_key)

SESSION_COOKIE = "session_id"


# ── Helpers ──────────────────────────────────────────────────────────


def _set_session_cookie(response: Response, spotify_id: str):
    token = signer.dumps(spotify_id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=60 * 60 * 24 * 30,
    )


def _get_session_user_id(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return signer.loads(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")


def _ensure_valid_token(user: User, db: Session) -> str:
    if not user.is_token_expired():
        return user.access_token

    new_tokens = spotify_service.refresh_access_token(user.refresh_token)
    user.access_token = new_tokens["access_token"]
    user.refresh_token = new_tokens["refresh_token"]
    user.token_expires_at = new_tokens["expires_at"]
    db.commit()
    return user.access_token


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/login")
def login():
    state = secrets.token_urlsafe(32)
    url = spotify_service.get_auth_url(state)
    return RedirectResponse(url)


@router.get("/callback")
def callback(
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{settings.frontend_url}?error={error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # 1. Exchange code for tokens
    tokens = spotify_service.exchange_code(code)

    # 2. Fetch Spotify profile
    profile = spotify_service.get_current_user(tokens["access_token"])

    # 3. Upsert user in DB
    stmt = select(User).where(User.spotify_id == profile["spotify_id"])
    user = db.execute(stmt).scalar_one_or_none()

    if user:
        user.access_token = tokens["access_token"]
        user.refresh_token = tokens["refresh_token"]
        user.token_expires_at = tokens["expires_at"]
        user.display_name = profile["display_name"]
        user.email = profile["email"]
        user.avatar_url = profile["avatar_url"]
    else:
        user = User(
            spotify_id=profile["spotify_id"],
            display_name=profile["display_name"],
            email=profile["email"],
            avatar_url=profile["avatar_url"],
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expires_at=tokens["expires_at"],
        )
        db.add(user)

    db.commit()

    # 4. Set session cookie and redirect to frontend
    response = RedirectResponse(settings.frontend_url)
    _set_session_cookie(response, profile["spotify_id"])
    return response


@router.get("/me", response_model=UserResponse)
def me(request: Request, db: Session = Depends(get_db)):
    spotify_id = _get_session_user_id(request)

    stmt = select(User).where(User.spotify_id == spotify_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_valid_token(user, db)
    return user


@router.post("/logout", response_model=StatusResponse)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return StatusResponse(ok=True, message="Logged out")
