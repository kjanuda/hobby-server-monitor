from falcon import testing

from app import app
from services.container_access_service import (
    ContainerAccessService,
)
from services.lxd_service import LXDService
from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
    get_registered_container,
)


client = testing.TestClient(app)
access = ContainerAccessService()
lxd = LXDService()

user = get_active_user("container_user")
record = get_registered_container()

assert user is not None, (
    "Active container user required."
)

assert record is not None, (
    "Registered container required."
)

USER_ID = user["id"]
CONTAINER_ID = record["id"]

container = lxd.client.containers.get(
    record["lxd_name"]
)

was_running = (
    container.status == "Running"
)


try:
    if not was_running:
        print("Starting terminal test container...")
        container.start(wait=True)

    print("1. Assign container")

    access.assign(
        USER_ID,
        CONTAINER_ID,
        actor_email="terminal-test@example.com",
    )

    token, headers = (
        create_authenticated_headers(
            client,
            USER_ID,
        )
    )

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

    assert (
        response.json["stdout"]
        == "terminal-ok"
    )

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

    hostname = (
        response.json["stdout"].strip()
    )

    print(
        "Container hostname:",
        hostname,
    )

    assert hostname == record["lxd_name"]

    print(
        "PASS: command ran inside "
        "expected LXD container"
    )


    print("\n4. Empty command")

    response = client.simulate_post(
        f"/api/containers/{CONTAINER_ID}/terminal",
        headers=headers,
        json={
            "command": ""
        },
    )

    assert response.status_code == 400

    print(
        "PASS: empty command rejected"
    )


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
        "PASS: unassigned user "
        "receives 403"
    )


finally:
    try:
        access.revoke(
            USER_ID,
            CONTAINER_ID,
            actor_email="terminal-test-cleanup@example.com",
        )
    except Exception:
        pass

    if "token" in globals():
        delete_test_session(token)

    container = lxd.client.containers.get(
        record["lxd_name"]
    )

    if (
        not was_running
        and container.status == "Running"
    ):
        container.stop(wait=True)


print(
    "\nPASS: secure container terminal "
    "API works correctly"
)
