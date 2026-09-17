from falcon import testing

from app import app
from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)
from db.database import get_connection
from repositories.container_repository import (
    ContainerRepository,
)
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
    if item["lxd_name"].startswith(
        "create-test-"
    )
]

assert records

record = max(
    records,
    key=lambda item: item["id"],
)

container_id = record["id"]
container_name = record["lxd_name"]

token = sessions.create_session(
    admin["id"]
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}


print("1. Wrong confirmation")

response = client.simulate_delete(
    f"/api/containers/{container_id}",
    headers=headers,
    json={
        "confirm_name": "wrong-name"
    },
)

assert response.status_code == 400
assert (
    containers.get_by_id(container_id)
    is not None
)

print(
    "PASS: incorrect confirmation "
    "does not delete container"
)


print("\n2. Correct confirmation")

response = client.simulate_delete(
    f"/api/containers/{container_id}",
    headers=headers,
    json={
        "confirm_name": container_name
    },
)

print("HTTP:", response.status_code)
print(response.json)

assert response.status_code == 200

print("PASS: deletion accepted")


print("\n3. Verify DB cleanup")

assert (
    containers.get_by_id(container_id)
    is None
)

print("PASS: DB registry row removed")


print("\n4. Verify LXD cleanup")

lxd_names = {
    item.name
    for item
    in lxd.client.containers.all()
}

assert container_name not in lxd_names

print("PASS: LXD container removed")


print("\n5. Verify assignments cleanup")

connection = get_connection()

try:
    access_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM container_access
        WHERE container_id = ?
        """,
        (container_id,),
    ).fetchone()["count"]

    assert access_count == 0

    audit = connection.execute(
        """
        SELECT *
        FROM audit_logs
        WHERE action = 'container.deleted'
          AND actor_email = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (admin["email"],),
    ).fetchone()

    assert audit is not None

finally:
    connection.close()

print(
    "PASS: assignments cleaned "
    "and deletion audited"
)


sessions.delete_session(token)

print(
    "\nPASS: safe container deletion "
    "works correctly"
)