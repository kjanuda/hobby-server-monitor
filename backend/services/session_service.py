import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from config import SESSION_TTL_SECONDS
from repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self):
        self.repository = SessionRepository()

    def create_session(self, user_id):
        self.cleanup_expired_sessions()

        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(raw_token)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=SESSION_TTL_SECONDS)
        )

        self.repository.create_session(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=self._format_time(expires_at),
        )

        return raw_token

    def get_user_from_token(self, raw_token):
        if not raw_token:
            return None

        token_hash = self._hash_token(raw_token)

        return self.repository.get_user_by_token_hash(
            token_hash=token_hash,
            current_time=self._format_time(
                datetime.now(timezone.utc)
            ),
        )

    def delete_session(self, raw_token):
        if not raw_token:
            return

        self.repository.delete_session(
            self._hash_token(raw_token)
        )

    def revoke_all_user_sessions(self, user_id):
        self.repository.delete_user_sessions(user_id)

    def cleanup_expired_sessions(self):
        self.repository.delete_expired_sessions(
            self._format_time(
                datetime.now(timezone.utc)
            )
        )

    @staticmethod
    def _hash_token(token):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _format_time(value):
        return value.strftime(
            "%Y-%m-%d %H:%M:%S"
        )