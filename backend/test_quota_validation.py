from services.quota_service import (
    QuotaService,
    QuotaValidationError,
)
from test_support import get_active_user


service = QuotaService()

owner = get_active_user(
    "container_user"
)

assert owner is not None

OWNER_ID = owner["id"]


print("1. Valid request")

service.validate_creation(
    owner_user_id=OWNER_ID,
    memory_bytes=256 * 1024 * 1024,
    cpu_cores=1,
    disk_bytes=1 * 1024 * 1024 * 1024,
    storage_pool="default",
)

print("PASS: valid request accepted")


print("\n2. Memory below minimum")

try:
    service.validate_creation(
        owner_user_id=OWNER_ID,
        memory_bytes=128 * 1024 * 1024,
        cpu_cores=1,
        disk_bytes=1 * 1024 * 1024 * 1024,
        storage_pool="default",
    )

    raise AssertionError(
        "Memory below minimum was accepted."
    )

except QuotaValidationError as exc:
    print(f"PASS: {exc}")


print("\n3. CPU above host capacity")

try:
    service.validate_creation(
        owner_user_id=OWNER_ID,
        memory_bytes=256 * 1024 * 1024,
        cpu_cores=999,
        disk_bytes=1 * 1024 * 1024 * 1024,
        storage_pool="default",
    )

    raise AssertionError(
        "CPU above host capacity was accepted."
    )

except QuotaValidationError as exc:
    print(f"PASS: {exc}")


print("\n4. Invalid storage pool")

try:
    service.validate_creation(
        owner_user_id=OWNER_ID,
        memory_bytes=256 * 1024 * 1024,
        cpu_cores=1,
        disk_bytes=1 * 1024 * 1024 * 1024,
        storage_pool="does-not-exist",
    )

    raise AssertionError(
        "Invalid storage pool was accepted."
    )

except QuotaValidationError as exc:
    print(f"PASS: {exc}")


print(
    "\nPASS: creation quota "
    "validation works"
)
