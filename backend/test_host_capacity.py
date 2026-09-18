from services.quota_service import (
    QuotaService,
    QuotaValidationError,
)


GIB = 1024 ** 3
TIB = 1024 ** 4


class FakeContainer:
    def __init__(
        self,
        memory,
        cpu,
        disk,
        pool="default",
    ):
        self.expanded_config = {
            "limits.memory": memory,
            "limits.cpu": str(cpu),
        }

        self.expanded_devices = {
            "root": {
                "type": "disk",
                "path": "/",
                "pool": pool,
                "size": disk,
            }
        }


class FakeContainers:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, name):
        return self.mapping[name]


class FakeClient:
    def __init__(self, mapping):
        self.containers = FakeContainers(
            mapping
        )


class FakeRepository:
    def __init__(self, records):
        self.records = records

    def list_all(self):
        return self.records

    def get_by_id(self, container_id):
        for record in self.records:
            if record["id"] == container_id:
                return record

        return None


def build_service(
    records,
    containers,
):
    service = QuotaService()

    service.container_repository = (
        FakeRepository(records)
    )

    service.lxd_service.client = (
        FakeClient(containers)
    )

    service.lxd_service.get_host_resources = (
        lambda: {
            "cpu": {
                "logical_cpus": 4,
            },
            "memory": {
                "total_bytes": 8 * GIB,
                "available_bytes": 8 * GIB,
            },
        }
    )

    service.lxd_service.get_storage_pools = (
        lambda: [
            {
                "name": "default",
                "space": {
                    "total_bytes": 1 * TIB,
                    "available_bytes": 1 * TIB,
                },
            }
        ]
    )

    return service


print("1. Creation aggregate RAM")

service = build_service(
    [
        {
            "id": 1,
            "lxd_name": "existing",
            "owner_user_id": None,
        }
    ],
    {
        "existing": FakeContainer(
            "3GiB",
            1,
            "10GiB",
        )
    },
)

try:
    service.validate_creation(
        owner_user_id=None,
        memory_bytes=6 * GIB,
        cpu_cores=1,
        disk_bytes=1 * GIB,
        storage_pool="default",
    )

    raise AssertionError(
        "RAM over-allocation was accepted."
    )

except QuotaValidationError as exc:
    assert "RAM allocation" in str(exc)
    print(f"PASS: {exc}")


print("\n2. Creation aggregate CPU")

service = build_service(
    [
        {
            "id": 1,
            "lxd_name": "existing",
            "owner_user_id": None,
        }
    ],
    {
        "existing": FakeContainer(
            "1GiB",
            3,
            "10GiB",
        )
    },
)

try:
    service.validate_creation(
        owner_user_id=None,
        memory_bytes=256 * 1024 * 1024,
        cpu_cores=2,
        disk_bytes=1 * GIB,
        storage_pool="default",
    )

    raise AssertionError(
        "CPU over-allocation was accepted."
    )

except QuotaValidationError as exc:
    assert "CPU allocation" in str(exc)
    print(f"PASS: {exc}")


print("\n3. Creation aggregate disk")

service = build_service(
    [
        {
            "id": 1,
            "lxd_name": "existing",
            "owner_user_id": None,
        }
    ],
    {
        "existing": FakeContainer(
            "1GiB",
            1,
            "900GiB",
        )
    },
)

try:
    service.validate_creation(
        owner_user_id=None,
        memory_bytes=256 * 1024 * 1024,
        cpu_cores=1,
        disk_bytes=200 * GIB,
        storage_pool="default",
    )

    raise AssertionError(
        "Disk over-allocation was accepted."
    )

except QuotaValidationError as exc:
    assert "storage pool allocation" in str(exc)
    print(f"PASS: {exc}")


print("\n4. Update excludes current allocation")

records = [
    {
        "id": 1,
        "lxd_name": "target",
        "owner_user_id": None,
    },
    {
        "id": 2,
        "lxd_name": "other",
        "owner_user_id": None,
    },
]

service = build_service(
    records,
    {
        "target": FakeContainer(
            "1GiB",
            1,
            "10GiB",
        ),
        "other": FakeContainer(
            "6GiB",
            1,
            "10GiB",
        ),
    },
)

try:
    service.validate_update(
        container_id=1,
        memory_bytes=3 * GIB,
        cpu_cores=1,
        disk_bytes=10 * GIB,
        storage_pool="default",
    )

    raise AssertionError(
        "Update RAM over-allocation "
        "was accepted."
    )

except QuotaValidationError as exc:
    assert "RAM allocation" in str(exc)
    print(f"PASS: {exc}")


print(
    "\nPASS: aggregate host capacity "
    "validation works correctly"
)