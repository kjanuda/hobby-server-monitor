import uuid

from falcon import testing

from app import app

from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
)


client = testing.TestClient(app)

admin = get_active_user("admin")
owner = get_active_user("container_user")

assert admin is not None
assert owner is not None

token, headers = create_authenticated_headers(
    client,
    admin["id"],
)

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
        "owner_user_id": owner["id"],
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

delete_test_session(token)