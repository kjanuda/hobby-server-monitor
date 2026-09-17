from falcon import testing

from app import app

from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)

from repositories.container_repository import (
    ContainerRepository,
)

from services.session_service import SessionService
from services.user_service import UserService


client = testing.TestClient(app)

sessions = SessionService()
users = UserService()
containers = ContainerRepository()

admin = users.get_user_by_email(
    BOOTSTRAP_ADMIN_EMAIL
)

records = [
    item
    for item in containers.list_all()
    if item["lxd_name"].startswith(
        "create-test-"
    )
]

assert records

record = max(
    records,
    key=lambda item: item["id"],
)

token = sessions.create_session(
    admin["id"]
)

response = client.simulate_patch(
    f"/api/containers/{record['id']}",
    headers={
        "Cookie": (
            f"{SESSION_COOKIE_NAME}={token}"
        )
    },
    json={
        "memory": "768MiB",
        "cpu_cores": 1,
        "cpu_allowance": 75,
        "disk": "3GiB",
    },
)

print("HTTP:", response.status_code)
print(response.json)

assert response.status_code == 200

sessions.delete_session(token)

print(
    "PASS: stopped container limits "
    "can be updated"
)