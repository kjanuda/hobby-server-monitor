from config import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
)
from db.database import get_connection
from services.session_service import SessionService


def create_authenticated_headers(
    client,
    user_id,
):
    sessions = SessionService()

    token = sessions.create_session(
        user_id
    )

    session_cookie = (
        f"{SESSION_COOKIE_NAME}={token}"
    )

    response = client.simulate_get(
        "/api/auth/me",
        headers={
            "Cookie": session_cookie
        },
    )

    if response.status_code != 200:
        sessions.delete_session(token)

        raise AssertionError(
            "Unable to create authenticated "
            f"test context: {response.text}"
        )

    csrf_token = response.json[
        "csrf_token"
    ]

    headers = {
        "Cookie": (
            f"{session_cookie}; "
            f"{CSRF_COOKIE_NAME}="
            f"{csrf_token}"
        ),
        "X-CSRF-Token": csrf_token,
    }

    return token, headers


def delete_test_session(token):
    SessionService().delete_session(
        token
    )


def get_active_user(role=None):
    connection = get_connection()

    try:
        if role:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE active = 1
                  AND invited = 1
                  AND role = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (role,),
            ).fetchone()

        else:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE active = 1
                  AND invited = 1
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


def get_registered_container(
    name_prefix=None,
):
    connection = get_connection()

    try:
        if name_prefix:
            row = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE lxd_name LIKE ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (f"{name_prefix}%",),
            ).fetchone()

        else:
            row = connection.execute(
                """
                SELECT *
                FROM containers
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()