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
ADMIN_ID = 2
CONTAINER_ID = 1


print("1. Assign container to user")

access.assign(
    USER_ID,
    CONTAINER_ID,
    actor_email="test-admin@example.com",
)

user_token = sessions.create_session(
    USER_ID
)

user_headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={user_token}"
    )
}


print("\n2. Assigned direct access")

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}",
    headers=user_headers,
)

assert response.status_code == 200

print(
    "PASS: assigned user can access "
    "container directly"
)


print("\n3. Revoke assignment")

access.revoke(
    USER_ID,
    CONTAINER_ID,
    actor_email="test-admin@example.com",
)


print("\n4. Unassigned direct access")

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}",
    headers=user_headers,
)

assert response.status_code == 403

print(
    "PASS: unassigned direct access "
    "returns 403"
)


print("\n5. Random container ID")

response = client.simulate_get(
    "/api/containers/99999",
    headers=user_headers,
)

assert response.status_code == 403

print(
    "PASS: container user cannot probe "
    "random container IDs"
)


print("\n6. Admin direct access")

admin_token = sessions.create_session(
    ADMIN_ID
)

admin_headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={admin_token}"
    )
}

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}",
    headers=admin_headers,
)

assert response.status_code == 200

print(
    "PASS: admin can access container"
)


sessions.delete_session(user_token)
sessions.delete_session(admin_token)

print(
    "\nPASS: direct container "
    "authorization works correctly"
)