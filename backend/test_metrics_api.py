from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from services.container_access_service import (
    ContainerAccessService,
)
from services.session_service import (
    SessionService,
)


client = testing.TestClient(app)
sessions = SessionService()
access = ContainerAccessService()

USER_ID = 1
CONTAINER_ID = 1


print("1. Assign container")

access.assign(
    USER_ID,
    CONTAINER_ID,
    actor_email="metrics-test@example.com",
)

token = sessions.create_session(USER_ID)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}


print("\n2. Query historical metrics")

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}/metrics",
    headers=headers,
    params={
        "hours": 24,
        "max_points": 360,
    },
)

print("HTTP:", response.status_code)
print(
    "Samples:",
    response.json.get("sample_count")
)
print(
    "Returned:",
    response.json.get("returned_count")
)

assert response.status_code == 200
assert response.json["sample_count"] >= 1
assert response.json["returned_count"] >= 1
assert len(response.json["points"]) >= 1

point = response.json["points"][-1]

assert "cpu_percent" in point
assert "memory_used_bytes" in point
assert "rx_bytes_per_second" in point

print(
    "PASS: assigned user can "
    "read historical metrics"
)


print("\n3. Revoke access")

access.revoke(
    USER_ID,
    CONTAINER_ID,
    actor_email="metrics-test@example.com",
)

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}/metrics",
    headers=headers,
)

assert response.status_code == 403

print(
    "PASS: unassigned user receives 403"
)


print("\n4. Invalid history range")

access.assign(
    USER_ID,
    CONTAINER_ID,
    actor_email="metrics-test@example.com",
)

response = client.simulate_get(
    f"/api/containers/{CONTAINER_ID}/metrics",
    headers=headers,
    params={
        "hours": 999,
    },
)

assert response.status_code == 400

print(
    "PASS: invalid history range rejected"
)


access.revoke(
    USER_ID,
    CONTAINER_ID,
    actor_email="metrics-test@example.com",
)

sessions.delete_session(token)

print(
    "\nPASS: historical metrics API "
    "works correctly"
)