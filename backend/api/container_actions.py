import falcon

from services.authorization import require_admin
from services.container_action_service import (
    ContainerActionError,
    ContainerActionService,
)


class ContainerActionResource:
    def __init__(self):
        self.service = ContainerActionService()

    @falcon.before(require_admin)
    def on_post(
        self,
        req,
        resp,
        container_id,
        action,
    ):
        try:
            container = self.service.perform(
                container_id=container_id,
                action=action,
                actor_email=req.context.user["email"],
            )

        except ContainerActionError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": f"Container {action} completed.",
            "container": container,
        }

        resp.status = falcon.HTTP_200