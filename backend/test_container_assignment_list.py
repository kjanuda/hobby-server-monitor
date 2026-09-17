from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from db.database import get_connection
from services.container_access_service import (
    ContainerAccessService,
)
from services.session_service import SessionService


client = testing.TestClient(app)
sessions = SessionService()
access = ContainerAccessService()


def get_test_records():
    connection = get_connection()

    try:
        admin = connection.execute(
            """
            SELECT *
            FROM users
            WHERE role = 'admin'
              AND active = 1
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

        container_user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE role = 'container_user'
              AND active = 1
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

        container = connection.execute(
            """
            SELECT *
            FROM containers
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

        return (
            dict(admin) if admin else None,
            (
                dict(container_user)
                if container_user
                else None
            ),
            (
                dict(container)
                if container
                else None
            ),
        )

    finally:
        connection.close()


admin, user, container = get_test_records()

assert admin, "Active admin user required."
assert user, "Active container user required."
assert container, "Registered container required."

ADMIN_ID = admin["id"]
USER_ID = user["id"]
CONTAINER_ID = container["id"]


print("1. No session")

response = client.simulate_get(
    f"/api/users/{USER_ID}/containers"
)

assert response.status_code == 401

print("PASS: unauthenticated request returns 401")


print("\n2. Container user cannot list assignments")

user_token = sessions.create_session(
    USER_ID
)

user_headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={user_token}"
    )
}

response = client.simulate_get(
    f"/api/users/{USER_ID}/containers",
    headers=user_headers,
)

assert response.status_code == 403

print("PASS: container user receives 403")


print("\n3. Assign test container")

access.assign(
    user_id=USER_ID,
    container_id=CONTAINER_ID,
    actor_email=admin["email"],
)


print("\n4. Admin lists assignments")

admin_token = sessions.create_session(
    ADMIN_ID
)

admin_headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={admin_token}"
    )
}

response = client.simulate_get(
    f"/api/users/{USER_ID}/containers",
    headers=admin_headers,
)

print("HTTP:", response.status_code)
print(response.json)

assert response.status_code == 200
assert response.json["user_id"] == USER_ID

assigned_ids = {
    item["id"]
    for item in response.json["containers"]
}

assert CONTAINER_ID in assigned_ids

print(
    "PASS: admin can list "
    "assigned containers"
)


print("\n5. Unknown user")

response = client.simulate_get(
    "/api/users/999999/containers",
    headers=admin_headers,
)

assert response.status_code == 404

print("PASS: unknown user returns 404")


print("\n6. Revoke and verify list")

access.revoke(
    user_id=USER_ID,
    container_id=CONTAINER_ID,
    actor_email=admin["email"],
)

response = client.simulate_get(
    f"/api/users/{USER_ID}/containers",
    headers=admin_headers,
)

assert response.status_code == 200

assigned_ids = {
    item["id"]
    for item in response.json["containers"]
}

assert CONTAINER_ID not in assigned_ids

print(
    "PASS: revoked container "
    "disappears from assignment list"
)


sessions.delete_session(
    user_token
)

sessions.delete_session(
    admin_token
)

print(
    "\nPASS: container assignment "
    "listing API works correctly"
)