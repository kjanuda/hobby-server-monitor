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
CONTAINER_NAME = container["lxd_name"]

token = None


try:
    print("1. Assign container")

    access.assign(
        user_id=USER_ID,
        container_id=CONTAINER_ID,
        actor_email="test-admin@example.com",
    )

    assert access.user_has_access(
        USER_ID,
        CONTAINER_ID,
    )

    print("PASS: assignment created")


    print("\n2. Container user list")

    token, headers = (
        create_authenticated_headers(
            client,
            USER_ID,
        )
    )

    response = client.simulate_get(
        "/api/containers",
        headers=headers,
    )

    assert response.status_code == 200

    names = {
        item["name"]
        for item in response.json["containers"]
    }

    assert CONTAINER_NAME in names

    print(
        "PASS: assigned container is visible"
    )


    print("\n3. Revoke assignment")

    access.revoke(
        user_id=USER_ID,
        container_id=CONTAINER_ID,
        actor_email="test-admin@example.com",
    )

    response = client.simulate_get(
        "/api/containers",
        headers=headers,
    )

    assert response.status_code == 200

    names = {
        item["name"]
        for item in response.json["containers"]
    }

    assert CONTAINER_NAME not in names

    print(
        "PASS: revoked container is hidden"
    )


finally:
    try:
        access.revoke(
            USER_ID,
            CONTAINER_ID,
            actor_email="test-cleanup@example.com",
        )
    except Exception:
        pass

    if token is not None:
        delete_test_session(token)


print(
    "\nPASS: container assignment "
    "and filtering work correctly"
)
