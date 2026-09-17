from repositories.container_repository import (
    ContainerRepository,
)
from services.lxd_service import LXDService


class ContainerRegistryService:
    def __init__(self):
        self.repository = ContainerRepository()
        self.lxd_service = LXDService()

    def sync_from_lxd(self):
        identities = (
            self.lxd_service
            .list_container_identities()
        )

        synced = []

        for identity in identities:
            container = (
                self.repository.upsert_container(
                    lxd_uuid=identity["lxd_uuid"],
                    lxd_name=identity["lxd_name"],
                    description=identity[
                        "description"
                    ],
                )
            )

            synced.append(container)

        return synced

    def list_registered_containers(self):
        return self.repository.list_all()