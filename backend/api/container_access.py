import falcon

from services.authorization import require_admin
from services.container_access_service import (
    ContainerAccessError,
    ContainerAccessService,
)


class ContainerAccessResource:
    def __init__(self):
        self.service = ContainerAccessService()

    @falcon.before(require_admin)
    def on_put(
        self,
        req,
        resp,
        user_id,
        container_id,
    ):
        try:
            container = self.service.assign(
                user_id=user_id,
                container_id=container_id,
                actor_email=req.context.user["email"],
            )

        except ContainerAccessError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": "Container assigned.",
            "container": container,
        }

        resp.status = falcon.HTTP_200

    @falcon.before(require_admin)
    def on_delete(
        self,
        req,
        resp,
        user_id,
        container_id,
    ):
        try:
            self.service.revoke(
                user_id=user_id,
                container_id=container_id,
                actor_email=req.context.user["email"],
            )

        except ContainerAccessError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": "Container access revoked."
        }

        resp.status = falcon.HTTP_200