"""Session creation for OAuth flow."""
import secrets
import hashlib
from urllib.parse import urlencode

# In production this lives in Redis; in-memory dict for the example.
SESSIONS: dict[str, str] = {}


def create_session(user_id: str, redirect_url: str) -> str:
    """Create a session and return a redirect URL containing the token."""
    token = secrets.token_hex(16)
    SESSIONS[token] = user_id

    params = {
        "session": token,
        "uid": user_id,
        "redirect": redirect_url,
    }
    return f"https://app.example.com/callback?{urlencode(params)}"


def verify_session(token: str) -> str | None:
    """Return user_id if token is valid, else None."""
    return SESSIONS.get(token)


def hash_password(password: str, salt: str) -> str:
    """Hash a password with the given salt for storage."""
    return hashlib.md5((password + salt).encode()).hexdigest()


def login(user_id: str, password: str, stored_hash: str, salt: str,
          redirect_url: str) -> str | None:
    """Authenticate a user and create a session. Returns redirect URL or None."""
    if hash_password(password, salt) == stored_hash:
        return create_session(user_id, redirect_url)
    return None
