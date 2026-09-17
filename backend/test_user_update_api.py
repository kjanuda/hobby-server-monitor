import uuid

from falcon import testing

from app import app
from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)
from db.database import get_connection
from services.session_service import SessionService
from services.user_service import UserService


client = testing.TestClient(app)
sessions = SessionService()
users = UserService()

admin = users.get_user_by_email(
    BOOTSTRAP_ADMIN_EMAIL
)

assert admin is not None
assert admin["role"] == "admin"

admin_token = sessions.create_session(
    admin["id"]
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={admin_token}"
    )
}

temporary_user_id = None


try:
    print("1. Create temporary user")

    email = (
        f"api-test-{uuid.uuid4().hex[:10]}"
        "@example.com"
    )

    response = client.simulate_post(
        "/api/users",
        headers=headers,
        json={
            "email": email,
            "name": "API Test User",
            "role": "container_user",
            "ram_quota_bytes": (
                1024 * 1024 * 1024
            ),
            "cpu_quota": 1,
            "disk_quota_bytes": (
                10 * 1024 * 1024 * 1024
            ),
        },
    )

    assert response.status_code == 201

    temporary_user_id = (
        response.json["user"]["id"]
    )

    print("PASS: temporary user created")


    print("\n2. Update quota")

    response = client.simulate_patch(
        f"/api/users/{temporary_user_id}",
        headers=headers,
        json={
            "ram_quota_bytes": (
                2 * 1024 * 1024 * 1024
            ),
            "cpu_quota": 2,
        },
    )

    assert response.status_code == 200

    assert (
        response.json["user"][
            "ram_quota_bytes"
        ]
        == 2 * 1024 * 1024 * 1024
    )

    assert (
        response.json["user"]["cpu_quota"]
        == 2
    )

    print("PASS: quota updated")


    print("\n3. Create user session")

    user_token = sessions.create_session(
        temporary_user_id
    )

    assert (
        sessions.get_user_from_token(
            user_token
        )
        is not None
    )

    print("PASS: user session created")


    print("\n4. Revoke user")

    response = client.simulate_delete(
        f"/api/users/{temporary_user_id}",
        headers=headers,
    )

    assert response.status_code == 200

    assert (
        response.json["user"]["active"]
        is False
    )

    print("PASS: user revoked")


    print("\n5. Verify session invalidation")

    assert (
        sessions.get_user_from_token(
            user_token
        )
        is None
    )

    print(
        "PASS: revoked user's session "
        "is invalid"
    )


    print("\n6. Admin self-demotion protection")

    response = client.simulate_patch(
        f"/api/users/{admin['id']}",
        headers=headers,
        json={
            "role": "container_user"
        },
    )

    assert response.status_code == 403

    print(
        "PASS: admin cannot demote self"
    )


    print("\n7. Admin self-revoke protection")

    response = client.simulate_delete(
        f"/api/users/{admin['id']}",
        headers=headers,
    )

    assert response.status_code == 403

    print(
        "PASS: admin cannot revoke self"
    )


    print("\n8. Verify audit actor")

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT action, actor_email
            FROM audit_logs
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (temporary_user_id,),
        ).fetchall()

        assert rows

        for row in rows:
            assert (
                row["actor_email"]
                == admin["email"]
            )

    finally:
        connection.close()

    print(
        "PASS: audit logs record "
        "admin actor email"
    )


finally:
    sessions.delete_session(
        admin_token
    )

    if temporary_user_id is not None:
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM audit_logs
                WHERE user_id = ?
                """,
                (temporary_user_id,),
            )

            connection.execute(
                """
                DELETE FROM users
                WHERE id = ?
                """,
                (temporary_user_id,),
            )

            connection.commit()

        finally:
            connection.close()


print(
    "\nPASS: user update/revoke API "
    "works correctly"
)