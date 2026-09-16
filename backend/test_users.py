from services.user_service import (
    UserAlreadyExistsError,
    UserService,
    UserValidationError,
)


service = UserService()


print("Existing users:")
print(service.list_users())


print("\nInvalid email test:")

try:
    service.create_user(
        email="not-an-email",
        name="Invalid User",
    )
except UserValidationError as exc:
    print(f"PASS: {exc}")


print("\nDuplicate email test:")

try:
    service.create_user(
        email="test@example.com",
        name="Duplicate User",
    )
except UserAlreadyExistsError as exc:
    print(f"PASS: {exc}")


print("\nNegative quota test:")

try:
    service.create_user(
        email="quota@example.com",
        ram_quota_bytes=-1,
    )
except UserValidationError as exc:
    print(f"PASS: {exc}")