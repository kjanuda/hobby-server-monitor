from db.database import get_connection
from services.user_service import UserService
from test_support import get_active_user


users = UserService()

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


connection = get_connection()

try:
    before_id = connection.execute(
        """
        SELECT COALESCE(
            MAX(id),
            0
        ) AS max_id
        FROM audit_logs
        """
    ).fetchone()["max_id"]

finally:
    connection.close()


try:
    print("1. Update user")

    users.update_user(
        user_id=USER_ID,
        name="Audit Regression User",
        role="container_user",
        ram_quota_bytes=(
            3 * 1024 * 1024 * 1024
        ),
        cpu_quota=2,
        disk_quota_bytes=(
            25 * 1024 * 1024 * 1024
        ),
    )

    print("PASS: update completed")


    print("\n2. Verify audit entry")

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE id > ?
              AND user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                before_id,
                USER_ID,
            ),
        ).fetchone()

    finally:
        connection.close()

    assert row is not None

    print(
        "PASS: user update "
        "created an audit entry"
    )


finally:
    users.update_user(
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
    "\nPASS: audit logging "
    "works correctly"
)
