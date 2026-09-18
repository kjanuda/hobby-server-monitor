import hashlib

from falcon import testing

from app import app
from config import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
)
from db.database import get_connection
from services.oauth_state_service import (
    OAuthStateService,
)
from services.session_service import (
    SessionService,
)
from test_support import get_active_user


client = testing.TestClient(app)

sessions = SessionService()
oauth_states = OAuthStateService()

user = get_active_user("container_user")

assert user is not None

USER_ID = user["id"]


print("1. Create authenticated session")

session_token = sessions.create_session(
    USER_ID
)

session_cookie = (
    f"{SESSION_COOKIE_NAME}="
    f"{session_token}"
)


print("\n2. Mutation without CSRF")

response = client.simulate_post(
    "/api/auth/logout",
    headers={
        "Cookie": session_cookie
    },
)

print("HTTP:", response.status_code)

assert response.status_code == 403

print(
    "PASS: missing CSRF token "
    "returns 403"
)


print("\n3. Get CSRF token")

response = client.simulate_get(
    "/api/auth/me",
    headers={
        "Cookie": session_cookie
    },
)

assert response.status_code == 200

csrf_token = response.json[
    "csrf_token"
]

assert csrf_token

print(
    "PASS: authenticated user "
    "receives CSRF token"
)


print("\n4. Wrong CSRF token")

response = client.simulate_post(
    "/api/auth/logout",
    headers={
        "Cookie": (
            f"{session_cookie}; "
            f"{CSRF_COOKIE_NAME}="
            f"{csrf_token}"
        ),
        "X-CSRF-Token": "wrong-token",
    },
)

assert response.status_code == 403

print(
    "PASS: mismatched CSRF token "
    "returns 403"
)


print("\n5. Valid CSRF token")

response = client.simulate_post(
    "/api/auth/logout",
    headers={
        "Cookie": (
            f"{session_cookie}; "
            f"{CSRF_COOKIE_NAME}="
            f"{csrf_token}"
        ),
        "X-CSRF-Token": csrf_token,
    },
)

assert response.status_code == 200

print(
    "PASS: valid CSRF token accepted"
)


print("\n6. Logout invalidates session")

response = client.simulate_get(
    "/api/auth/me",
    headers={
        "Cookie": session_cookie
    },
)

assert response.status_code == 401

print(
    "PASS: session invalid after logout"
)


print("\n7. Expired session cleanup")

expired_raw = "expired-test-session"

expired_hash = hashlib.sha256(
    expired_raw.encode("utf-8")
).hexdigest()

connection = get_connection()

try:
    connection.execute(
        """
        INSERT OR REPLACE INTO sessions (
            token_hash,
            user_id,
            expires_at
        )
        VALUES (?, ?, ?)
        """,
        (
            expired_hash,
            USER_ID,
            "2000-01-01 00:00:00",
        ),
    )

    connection.commit()

finally:
    connection.close()


fresh_token = sessions.create_session(
    USER_ID
)

connection = get_connection()

try:
    row = connection.execute(
        """
        SELECT id
        FROM sessions
        WHERE token_hash = ?
        """,
        (expired_hash,),
    ).fetchone()

finally:
    connection.close()

assert row is None

sessions.delete_session(
    fresh_token
)

print(
    "PASS: expired sessions "
    "are automatically removed"
)


print("\n8. Expired OAuth state cleanup")

expired_state_hash = hashlib.sha256(
    b"expired-oauth-state"
).hexdigest()

connection = get_connection()

try:
    connection.execute(
        """
        INSERT OR REPLACE INTO oauth_states (
            state_hash,
            code_verifier,
            expires_at
        )
        VALUES (?, ?, ?)
        """,
        (
            expired_state_hash,
            "expired-verifier",
            "2000-01-01 00:00:00",
        ),
    )

    connection.commit()

finally:
    connection.close()


new_state, _ = oauth_states.create_state()

connection = get_connection()

try:
    row = connection.execute(
        """
        SELECT id
        FROM oauth_states
        WHERE state_hash = ?
        """,
        (expired_state_hash,),
    ).fetchone()

finally:
    connection.close()

assert row is None

oauth_states.consume_state(
    new_state
)

print(
    "PASS: expired OAuth states "
    "are automatically removed"
)


print(
    "\nPASS: authentication "
    "hardening works correctly"
)