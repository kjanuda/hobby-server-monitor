from pathlib import Path

from config import BOOTSTRAP_ADMIN_EMAIL
from db.database import DEFAULT_DB_PATH, get_connection
from services.user_service import UserService


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def seed_bootstrap_admin():
    if not BOOTSTRAP_ADMIN_EMAIL:
        print("Bootstrap admin not configured.")
        return

    service = UserService()

    existing_user = service.get_user_by_email(
        BOOTSTRAP_ADMIN_EMAIL
    )

    if existing_user:
        if existing_user["role"] != "admin":
            raise RuntimeError(
                "BOOTSTRAP_ADMIN_EMAIL already belongs to "
                "a non-admin user. Refusing automatic "
                "privilege escalation."
            )

        print(
            f"Bootstrap admin already exists: "
            f"{BOOTSTRAP_ADMIN_EMAIL}"
        )
        return

    service.create_user(
        email=BOOTSTRAP_ADMIN_EMAIL,
        name="Bootstrap Admin",
        role="admin",
    )

    print(
        f"Bootstrap admin created: "
        f"{BOOTSTRAP_ADMIN_EMAIL}"
    )


def initialize_database():
    schema = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    connection = get_connection()

    try:
        connection.executescript(schema)
        connection.commit()

    finally:
        connection.close()

    seed_bootstrap_admin()

    print("Database initialized successfully.")
    print(f"Database path: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    initialize_database()