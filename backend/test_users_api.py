from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from services.session_service import SessionService


client = testing.TestClient(app)
sessions = SessionService()


print("1. Unauthenticated users request")

response = client.simulate_get(
    "/api/users"
)

assert response.status_code == 401

print("PASS: unauthenticated request returns 401")


print("\n2. Container user request")

user_token = sessions.create_session(
    user_id=1
)

response = client.simulate_get(
    "/api/users",
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={user_token}"
        )
    },
)

assert response.status_code == 403

sessions.delete_session(user_token)

print("PASS: container user receives 403")


print("\n3. Admin users request")

admin_token = sessions.create_session(
    user_id=2
)

response = client.simulate_get(
    "/api/users",
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={admin_token}"
        )
    },
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
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={admin_token}"
        )
    },
    json={
        "email": "test@example.com",
        "role": "container_user",
        "ram_quota_bytes": 2147483648,
        "cpu_quota": 2,
        "disk_quota_bytes": 21474836480,
    },
)

assert response.status_code == 409

print(
    "PASS: duplicate user invitation returns 409"
)

sessions.delete_session(admin_token)


print(
    "\nPASS: admin users API authorization "
    "works correctly"
)