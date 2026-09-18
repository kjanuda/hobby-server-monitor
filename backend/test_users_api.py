from falcon import testing

from app import app
from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
)


client = testing.TestClient(app)

container_user = get_active_user(
    "container_user"
)

admin = get_active_user(
    "admin"
)

assert container_user is not None
assert admin is not None


print("1. Unauthenticated users request")

response = client.simulate_get(
    "/api/users"
)

assert response.status_code == 401

print(
    "PASS: unauthenticated request "
    "returns 401"
)


print("\n2. Container user request")

user_token, user_headers = (
    create_authenticated_headers(
        client,
        container_user["id"],
    )
)

try:
    response = client.simulate_get(
        "/api/users",
        headers=user_headers,
    )

    assert response.status_code == 403

finally:
    delete_test_session(
        user_token
    )

print(
    "PASS: container user receives 403"
)


print("\n3. Admin users request")

admin_token, admin_headers = (
    create_authenticated_headers(
        client,
        admin["id"],
    )
)

try:
    response = client.simulate_get(
        "/api/users",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "users" in response.json

    print(
        f"PASS: admin can list "
        f"{response.json['count']} users"
    )


    print("\n4. Duplicate invitation")

    response = client.simulate_post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": container_user["email"],
            "role": "container_user",
            "ram_quota_bytes": (
                2 * 1024 * 1024 * 1024
            ),
            "cpu_quota": 2,
            "disk_quota_bytes": (
                20 * 1024 * 1024 * 1024
            ),
        },
    )

    assert response.status_code == 409

    print(
        "PASS: duplicate user invitation "
        "returns 409"
    )

finally:
    delete_test_session(
        admin_token
    )


print(
    "\nPASS: admin users API "
    "authorization works correctly"
)
