import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from repositories.oauth_state_repository import (
    OAuthStateRepository,
)


class OAuthStateService:
    STATE_TTL_SECONDS = 600

    def __init__(self):
        self.repository = OAuthStateRepository()

    def create_state(self):
        state = secrets.token_urlsafe(32)

        # PKCE verifier length is intentionally longer.
        code_verifier = secrets.token_urlsafe(64)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=self.STATE_TTL_SECONDS)
        )

        self.repository.create_state(
            state_hash=self._hash_state(state),
            code_verifier=code_verifier,
            expires_at=self._format_time(expires_at),
        )

        return state, code_verifier

    def consume_state(self, state):
        if not state:
            return None

        return self.repository.consume_state(
            state_hash=self._hash_state(state),
            current_time=self._format_time(
                datetime.now(timezone.utc)
            ),
        )

    @staticmethod
    def _hash_state(state):
        return hashlib.sha256(
            state.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _format_time(value):
        return value.strftime(
            "%Y-%m-%d %H:%M:%S"
        )