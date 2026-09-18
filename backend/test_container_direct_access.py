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
admin = get_active_user("admin")
container = get_registered_container()

assert user is not None
assert admin is not None
assert container is not None

USER_ID = user["id"]
ADMIN_ID = admin["id"]
CONTAINER_ID = container["id"]

user_token = None
admin_token = None


try:
    print("1. Assign container to user")

    access.assign(
        USER_ID,
        CONTAINER_ID,
        actor_email=admin["email"],
    )

    user_token, user_headers = (
        create_authenticated_headers(
            client,
            USER_ID,
        )
    )


    print("\n2. Assigned direct access")

    response = client.simulate_get(
        f"/api/containers/{CONTAINER_ID}",
        headers=user_headers,
    )

    assert response.status_code == 200

    print(
        "PASS: assigned user can access "
        "container directly"
    )


    print("\n3. Revoke assignment")

    access.revoke(
        USER_ID,
        CONTAINER_ID,
        actor_email=admin["email"],
    )


    print("\n4. Unassigned direct access")

    response = client.simulate_get(
        f"/api/containers/{CONTAINER_ID}",
        headers=user_headers,
    )

    assert response.status_code == 403

    print(
        "PASS: unassigned direct access "
        "returns 403"
    )


    print("\n5. Random container ID")

    response = client.simulate_get(
        "/api/containers/999999",
        headers=user_headers,
    )

    assert response.status_code == 403

    print(
        "PASS: container user cannot probe "
        "random container IDs"
    )


    print("\n6. Admin direct access")

    admin_token, admin_headers = (
        create_authenticated_headers(
            client,
            ADMIN_ID,
        )
    )

    response = client.simulate_get(
        f"/api/containers/{CONTAINER_ID}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    print(
        "PASS: admin can access container"
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

    if user_token is not None:
        delete_test_session(user_token)

    if admin_token is not None:
        delete_test_session(admin_token)


print(
    "\nPASS: direct container "
    "authorization works correctly"
)
