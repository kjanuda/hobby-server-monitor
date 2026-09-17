from falcon import testing

from app import app
from config import (
    BOOTSTRAP_ADMIN_EMAIL,
    SESSION_COOKIE_NAME,
)
from repositories.container_repository import ContainerRepository
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
    if item["lxd_name"].startswith("create-test-")
]

assert records

record = max(
    records,
    key=lambda item: item["id"],
)

container_id = record["id"]

token = sessions.create_session(
    admin["id"]
)

headers = {
    "Cookie": (
        f"{SESSION_COOKIE_NAME}={token}"
    )
}


def run_action(action):
    response = client.simulate_post(
        f"/api/containers/{container_id}/actions/{action}",
        headers=headers,
    )

    print(
        action,
        response.status_code,
        response.json.get(
            "container",
            {},
        ).get("status"),
    )

    assert response.status_code == 200

    return response


print("1. Start")
response = run_action("start")
assert response.json["container"]["status"] == "Running"
print("PASS: started")


print("\n2. Restart")
response = run_action("restart")
assert response.json["container"]["status"] == "Running"
print("PASS: restarted")


print("\n3. Freeze")
run_action("freeze")
print("PASS: frozen")


print("\n4. Unfreeze")
response = run_action("unfreeze")
assert response.json["container"]["status"] == "Running"
print("PASS: unfrozen")


print("\n5. Stop")
response = run_action("stop")
assert response.json["container"]["status"] == "Stopped"
print("PASS: stopped")


print("\n6. Invalid action")

response = client.simulate_post(
    f"/api/containers/{container_id}/actions/invalid",
    headers=headers,
)

assert response.status_code == 400

print("PASS: invalid action rejected")


sessions.delete_session(token)

print(
    "\nPASS: container lifecycle actions work correctly"
)