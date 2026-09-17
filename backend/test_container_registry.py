from services.container_registry_service import (
    ContainerRegistryService,
)


service = ContainerRegistryService()


print("Syncing LXD containers...")

containers = service.sync_from_lxd()

assert containers

print(f"PASS: synced {len(containers)} container(s)")


print("\nRegistered containers:")

registered = service.list_registered_containers()

for container in registered:
    print(
        container["id"],
        container["lxd_name"],
        container["lxd_uuid"],
    )


assert any(
    container["lxd_name"] == "test-container"
    for container in registered
)

print(
    "\nPASS: LXD container registry "
    "sync works correctly"
)