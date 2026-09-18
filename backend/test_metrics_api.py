from falcon import testing

from app import app
from services.container_access_service import (
    ContainerAccessService,
)
from test_support import (
    create_authenticated_headers,
    delete_test_session,
    get_active_user,
    get_registered_container,
)


client = testing.TestClient(app)
access = ContainerAccessService()

user = get_active_user("container_user")
container = get_registered_container()

assert user is not None
assert container is not None

USER_ID = user["id"]
CONTAINER_ID = container["id"]

token = None


try:
    print("1. Assign container")

    access.assign(
        USER_ID,
        CONTAINER_ID,
        actor_email="metrics-test@example.com",
    )

    token, headers = (
        create_authenticated_headers(
            client,
            USER_ID,
        )
    )


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
        response.json.get(
            "sample_count"
        ),
    )

    print(
        "Returned:",
        response.json.get(
            "returned_count"
        ),
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


finally:
    try:
        access.revoke(
            USER_ID,
            CONTAINER_ID,
            actor_email="metrics-test-cleanup@example.com",
        )
    except Exception:
        pass

    if token is not None:
        delete_test_session(token)


print(
    "\nPASS: historical metrics API "
    "works correctly"
)
