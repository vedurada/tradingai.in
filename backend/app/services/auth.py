from __future__ import annotations

import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("tradingai.auth")


class User:
    def __init__(self, username: str, password_hash: str, role: str = "user") -> None:
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def to_dict(self) -> dict:
        return {"username": self.username, "role": self.role}


class AuthService:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._sessions: dict[str, dict] = {}
        self._secret = secrets.token_hex(32)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str, role: str = "user") -> bool:
        if username in self._users:
            return False
        self._users[username] = User(username, self._hash_password(password), role)
        logger.info(f"User registered: {username}")
        return True

    def login(self, username: str, password: str) -> Optional[str]:
        user = self._users.get(username)
        if not user or user.password_hash != self._hash_password(password):
            logger.warning(f"Failed login attempt for {username}")
            return None
        token = secrets.token_hex(32)
        self._sessions[token] = {
            "username": username,
            "role": user.role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        }
        logger.info(f"User logged in: {username}")
        return token

    def logout(self, token: str) -> bool:
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def validate_token(self, token: str) -> Optional[dict]:
        session = self._sessions.get(token)
        if not session:
            return None
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            del self._sessions[token]
            return None
        return {"username": session["username"], "role": session["role"]}

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def list_users(self) -> list[dict]:
        return [u.to_dict() for u in self._users.values()]


auth_service = AuthService()

auth_service.register("admin", "admin123", "admin")
auth_service.register("trader", "trade123", "trader")