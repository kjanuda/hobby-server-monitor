from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from services.container_access_service import (
    ContainerAccessService,
)
from services.session_service import SessionService


client = testing.TestClient(app)
sessions = SessionService()
access = ContainerAccessService()

USER_ID = 1
CONTAINER_ID = 1


print("1. Assign container")

access.assign(
    user_id=USER_ID,
    container_id=CONTAINER_ID,
    actor_email="test-admin@example.com",
)

assert access.user_has_access(
    USER_ID,
    CONTAINER_ID,
)

print("PASS: assignment created")


print("\n2. Container user list")

token = sessions.create_session(USER_ID)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}

response = client.simulate_get(
    "/api/containers",
    headers=headers,
)

assert response.status_code == 200
assert response.json["count"] == 1

assert (
    response.json["containers"][0]["name"]
    == "test-container"
)

print(
    "PASS: assigned container is visible"
)


print("\n3. Revoke assignment")

access.revoke(
    user_id=USER_ID,
    container_id=CONTAINER_ID,
    actor_email="test-admin@example.com",
)

response = client.simulate_get(
    "/api/containers",
    headers=headers,
)

assert response.status_code == 200
assert response.json["count"] == 0

print(
    "PASS: revoked container is hidden"
)

sessions.delete_session(token)

print(
    "\nPASS: container assignment "
    "and filtering work correctly"
)