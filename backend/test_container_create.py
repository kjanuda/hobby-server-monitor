import uuid

from falcon import testing

from app import app
from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)
from services.session_service import SessionService
from services.user_service import UserService


client = testing.TestClient(app)
sessions = SessionService()
users = UserService()

admin = users.get_user_by_email(
    BOOTSTRAP_ADMIN_EMAIL
)

assert admin is not None

token = sessions.create_session(
    admin["id"]
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}

name = (
    "create-test-"
    + uuid.uuid4().hex[:8]
)

print(
    f"Creating container: {name}"
)

response = client.simulate_post(
    "/api/containers",
    headers=headers,
    json={
        "name": name,
        "image": "24.04",
        "memory": "512MiB",
        "cpu_cores": 1,
        "cpu_allowance": 50,
        "disk": "2GiB",
        "storage_pool": "default",
        "network": "lxdbr0",
        "owner_user_id": 1,
        "ephemeral": False,
        "autostart": True,
        "description": (
            "Automated container creation test"
        ),
    },
)

print(
    "HTTP:",
    response.status_code,
)

print(response.json)

assert response.status_code == 201

container_id = (
    response.json["container"]["id"]
)

print(
    f"PASS: created DB container "
    f"id={container_id}"
)

sessions.delete_session(token)