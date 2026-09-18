from services.user_service import (
    UserService,
    UserValidationError,
)
from test_support import get_active_user


service = UserService()

user = get_active_user(
    "container_user"
)

assert user is not None

USER_ID = user["id"]

original = {
    "name": user["name"],
    "role": user["role"],
    "ram_quota_bytes": (
        user["ram_quota_bytes"]
    ),
    "cpu_quota": user["cpu_quota"],
    "disk_quota_bytes": (
        user["disk_quota_bytes"]
    ),
}


try:
    print("1. List users")

    users = service.list_users()

    assert users

    print(
        f"PASS: {len(users)} user(s) returned"
    )


    print("\n2. Update user")

    updated_user = service.update_user(
        user_id=USER_ID,
        name="Regression Test User",
        role="container_user",
        ram_quota_bytes=(
            3 * 1024 * 1024 * 1024
        ),
        cpu_quota=2,
        disk_quota_bytes=(
            25 * 1024 * 1024 * 1024
        ),
    )

    assert updated_user["id"] == USER_ID

    assert (
        updated_user["name"]
        == "Regression Test User"
    )

    print("PASS: user updated")


    print("\n3. Invalid role")

    try:
        service.update_user(
            user_id=USER_ID,
            name="Invalid Role User",
            role="super_admin",
            ram_quota_bytes=1,
            cpu_quota=1,
            disk_quota_bytes=1,
        )

        raise AssertionError(
            "Invalid role was accepted."
        )

    except UserValidationError as exc:
        print(f"PASS: {exc}")


    print("\n4. Missing user")

    try:
        service.get_user_by_id(
            999999
        )

        raise AssertionError(
            "Missing user was accepted."
        )

    except UserValidationError as exc:
        print(f"PASS: {exc}")


finally:
    service.update_user(
        user_id=USER_ID,
        name=original["name"],
        role=original["role"],
        ram_quota_bytes=(
            original["ram_quota_bytes"]
        ),
        cpu_quota=original[
            "cpu_quota"
        ],
        disk_quota_bytes=(
            original["disk_quota_bytes"]
        ),
    )


print(
    "\nPASS: user management "
    "service works correctly"
)
