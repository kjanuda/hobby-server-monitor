from falcon import testing

from app import app
from config import SESSION_COOKIE_NAME
from services.session_service import (
    SessionService,
)


client = testing.TestClient(app)
sessions = SessionService()

USER_ID = 1


print("1. No session")

response = client.simulate_get(
    "/api/me/quota"
)

assert response.status_code == 401

print(
    "PASS: unauthenticated request "
    "returns 401"
)


print("\n2. Container user own quota")

token = sessions.create_session(
    USER_ID
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}

response = client.simulate_get(
    "/api/me/quota",
    headers=headers,
)

print("HTTP:", response.status_code)
print(response.json)

assert response.status_code == 200

assert "limits" in response.json
assert "used" in response.json
assert "remaining" in response.json
assert "unlimited" in response.json

assert (
    response.json["user_id"]
    == USER_ID
)

print(
    "PASS: user can read own "
    "quota usage"
)


print("\n3. Verify quota math")

limits = response.json["limits"]
used = response.json["used"]
remaining = response.json["remaining"]

if limits["ram_bytes"] > 0:
    assert (
        remaining["ram_bytes"]
        == max(
            limits["ram_bytes"]
            - used["ram_bytes"],
            0,
        )
    )

if limits["cpu_cores"] > 0:
    assert (
        remaining["cpu_cores"]
        == max(
            limits["cpu_cores"]
            - used["cpu_cores"],
            0,
        )
    )

if limits["disk_bytes"] > 0:
    assert (
        remaining["disk_bytes"]
        == max(
            limits["disk_bytes"]
            - used["disk_bytes"],
            0,
        )
    )

print(
    "PASS: remaining quota "
    "calculation is correct"
)


sessions.delete_session(token)

print(
    "\nPASS: own quota API "
    "works correctly"
)