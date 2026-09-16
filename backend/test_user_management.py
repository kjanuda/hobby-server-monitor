from services.user_service import (
    UserService,
    UserValidationError,
)


service = UserService()


print("All users:")
print(service.list_users())


print("\nUpdating user 1:")

updated_user = service.update_user(
    user_id=1,
    name="Updated Test User",
    role="container_user",
    ram_quota_bytes=3 * 1024 * 1024 * 1024,
    cpu_quota=2,
    disk_quota_bytes=25 * 1024 * 1024 * 1024,
)

print(updated_user)


print("\nInvalid role test:")

try:
    service.update_user(
        user_id=1,
        name="Invalid Role User",
        role="super_admin",
        ram_quota_bytes=1,
        cpu_quota=1,
        disk_quota_bytes=1,
    )

except UserValidationError as exc:
    print(f"PASS: {exc}")


print("\nMissing user test:")

try:
    service.get_user_by_id(99999)

except UserValidationError as exc:
    print(f"PASS: {exc}")