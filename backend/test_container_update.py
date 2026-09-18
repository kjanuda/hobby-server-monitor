from falcon import testing

from app import app
from repositories.container_repository import (
    ContainerRepository,
)
from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
)


client = testing.TestClient(app)
containers = ContainerRepository()

admin = get_active_user("admin")

assert admin is not None

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

token, headers = create_authenticated_headers(
    client,
    admin["id"],
)

response = client.simulate_patch(
    f"/api/containers/{record['id']}",
    headers=headers,
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

delete_test_session(token)

print(
    "PASS: stopped container limits "
    "can be updated"
)