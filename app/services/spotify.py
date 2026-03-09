from datetime import datetime, timedelta, timezone
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config import get_settings

settings = get_settings()

SCOPES = "user-read-private user-read-email"


class SpotifyService:
    """Handles all communication with Spotify's API via spotipy."""

    def __init__(self):
        self.oauth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.spotify_redirect_uri,
            scope=SCOPES,
        )

    def get_auth_url(self, state: str) -> str:
        return self.oauth.get_authorize_url(state=state)

    def exchange_code(self, code: str) -> dict[str, Any]:
        token_info = self.oauth.get_access_token(code, as_dict=True, check_cache=False)
        return {
            "access_token": token_info["access_token"],
            "refresh_token": token_info["refresh_token"],
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=token_info["expires_in"]),
        }

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        token_info = self.oauth.refresh_access_token(refresh_token)
        return {
            "access_token": token_info["access_token"],
            "refresh_token": token_info.get("refresh_token", refresh_token),
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=token_info["expires_in"]),
        }

    def get_current_user(self, access_token: str) -> dict[str, Any]:
        sp = spotipy.Spotify(auth=access_token)
        data = sp.current_user()
        images = data.get("images", [])
        return {
            "spotify_id": data["id"],
            "display_name": data.get("display_name"),
            "email": data.get("email"),
            "avatar_url": images[0]["url"] if images else None,
        }


spotify_service = SpotifyService()
