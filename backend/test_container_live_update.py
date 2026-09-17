from falcon import testing

from app import app
from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)
from repositories.container_repository import ContainerRepository
from services.lxd_service import LXDService
from services.session_service import SessionService
from services.user_service import UserService


client = testing.TestClient(app)
sessions = SessionService()
users = UserService()
containers = ContainerRepository()
lxd = LXDService()

admin = users.get_user_by_email(
    BOOTSTRAP_ADMIN_EMAIL
)

records = [
    item
    for item in containers.list_all()
    if item["lxd_name"].startswith("create-test-")
]

assert records

record = max(
    records,
    key=lambda item: item["id"],
)

container = lxd.client.containers.get(
    record["lxd_name"]
)

if container.status != "Running":
    print("Starting test container...")
    container.start(wait=True)

token = sessions.create_session(
    admin["id"]
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}

try:
    print("Updating limits while container is running...")

    response = client.simulate_patch(
        f"/api/containers/{record['id']}",
        headers=headers,
        json={
            "memory": "896MiB",
            "cpu_cores": 1,
            "cpu_allowance": 60,
        },
    )

    print("HTTP:", response.status_code)
    print(
        "Status:",
        response.json.get(
            "container",
            {},
        ).get("status"),
    )

    assert response.status_code == 200
    assert (
        response.json["container"]["status"]
        == "Running"
    )

    assert (
        response.json["container"]["limits"]["memory"]
        == "939524096B"
    )

    print(
        "PASS: limits updated while "
        "container remained running"
    )

finally:
    container = lxd.client.containers.get(
        record["lxd_name"]
    )

    if container.status == "Running":
        container.stop(wait=True)

    sessions.delete_session(token)