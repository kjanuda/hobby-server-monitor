from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from services.session_service import SessionService


client = testing.TestClient(app)
sessions = SessionService()


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

user_token = sessions.create_session(
    user_id=1
)

response = client.simulate_get(
    "/api/containers",
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={user_token}"
        )
    },
)

assert response.status_code == 403

print(
    "PASS: container user receives 403"
)

sessions.delete_session(user_token)


print("\n4. Admin accessing protected endpoint")

admin_token = sessions.create_session(
    user_id=2
)

response = client.simulate_get(
    "/api/containers",
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={admin_token}"
        )
    },
)

assert response.status_code == 200

print(
    "PASS: admin can access protected endpoint"
)

sessions.delete_session(admin_token)


print(
    "\nPASS: centralized authentication "
    "and authorization work correctly"
)