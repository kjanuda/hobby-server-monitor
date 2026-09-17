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
    USER_ID,
    CONTAINER_ID,
    actor_email="terminal-test@example.com",
)

token = sessions.create_session(USER_ID)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}


print("\n2. Execute command")

response = client.simulate_post(
    f"/api/containers/{CONTAINER_ID}/terminal",
    headers=headers,
    json={
        "command": "printf terminal-ok"
    },
)

print("HTTP:", response.status_code)
print(response.json)

assert response.status_code == 200
assert response.json["exit_code"] == 0
assert response.json["stdout"] == "terminal-ok"

print(
    "PASS: command executed inside "
    "assigned container"
)


print("\n3. Verify container identity")

response = client.simulate_post(
    f"/api/containers/{CONTAINER_ID}/terminal",
    headers=headers,
    json={
        "command": "hostname"
    },
)

assert response.status_code == 200

print(
    "Container hostname:",
    response.json["stdout"].strip(),
)


print("\n4. Empty command")

response = client.simulate_post(
    f"/api/containers/{CONTAINER_ID}/terminal",
    headers=headers,
    json={"command": ""},
)

assert response.status_code == 400

print("PASS: empty command rejected")


print("\n5. Revoke access")

access.revoke(
    USER_ID,
    CONTAINER_ID,
    actor_email="terminal-test@example.com",
)

response = client.simulate_post(
    f"/api/containers/{CONTAINER_ID}/terminal",
    headers=headers,
    json={
        "command": "uname -s"
    },
)

assert response.status_code == 403

print(
    "PASS: unassigned user receives 403"
)


sessions.delete_session(token)

print(
    "\nPASS: secure container terminal "
    "API works correctly"
)