from falcon import testing

from app import app
from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
)


client = testing.TestClient(app)

user = get_active_user("container_user")
admin = get_active_user("admin")

assert user is not None
assert admin is not None


print("1. Public health endpoint")

response = client.simulate_get(
    "/api/health"
)

assert response.status_code == 200

print("PASS: /api/health is public")


print("\n2. Protected endpoint without session")

response = client.simulate_get(
    "/api/containers"
)

assert response.status_code == 401

print(
    "PASS: unauthenticated request returns 401"
)


print("\n3. Container user attempting admin endpoint")

user_token, user_headers = (
    create_authenticated_headers(
        client,
        user["id"],
    )
)

try:
    response = client.simulate_get(
        "/api/users",
        headers=user_headers,
    )

    assert response.status_code == 403

finally:
    delete_test_session(user_token)

print(
    "PASS: container user receives 403 "
    "for admin-only endpoint"
)


print("\n4. Admin accessing admin endpoint")

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

finally:
    delete_test_session(admin_token)

print(
    "PASS: admin can access "
    "admin-only endpoint"
)


print(
    "\nPASS: centralized authentication "
    "and authorization work correctly"
)
