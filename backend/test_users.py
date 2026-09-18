import uuid

from services.user_service import (
    UserAlreadyExistsError,
    UserService,
    UserValidationError,
)
from test_support import get_active_user


service = UserService()

existing_user = get_active_user(
    "container_user"
)

assert existing_user is not None


print("1. List users")

users = service.list_users()

assert users

print(
    f"PASS: {len(users)} user(s) returned"
)


print("\n2. Invalid email")

try:
    service.create_user(
        email="not-an-email",
        name="Invalid User",
    )

    raise AssertionError(
        "Invalid email was accepted."
    )

except UserValidationError as exc:
    print(f"PASS: {exc}")


print("\n3. Duplicate email")

try:
    service.create_user(
        email=existing_user["email"],
        name="Duplicate User",
    )

    raise AssertionError(
        "Duplicate email was accepted."
    )

except UserAlreadyExistsError as exc:
    print(
        "PASS: duplicate email rejected"
    )


print("\n4. Negative quota")

temporary_email = (
    f"quota-{uuid.uuid4().hex[:8]}"
    "@example.com"
)

try:
    service.create_user(
        email=temporary_email,
        name="Quota Test User",
        ram_quota_bytes=-1,
    )

    raise AssertionError(
        "Negative quota was accepted."
    )

except UserValidationError as exc:
    print(f"PASS: {exc}")


print(
    "\nPASS: user validation "
    "works correctly"
)
