import falcon

from services.container_access_service import (
    ContainerAccessForbiddenError,
)
from services.terminal_service import (
    TerminalContainerNotFoundError,
    TerminalExecutionError,
    TerminalSecurityError,
    TerminalService,
    TerminalStateError,
    TerminalValidationError,
)


class ContainerTerminalResource:
    def __init__(self):
        self.service = TerminalService()

    def on_post(
        self,
        req,
        resp,
        container_id,
    ):
        data = req.media or {}

        try:
            result = self.service.execute(
                user=req.context.user,
                container_id=container_id,
                command=data.get("command"),
            )

        except ContainerAccessForbiddenError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_403
            return

        except TerminalContainerNotFoundError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_404
            return

        except TerminalStateError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_409
            return

        except TerminalSecurityError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_403
            return

        except TerminalValidationError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_400
            return

        except TerminalExecutionError as exc:
            resp.media = {"error": str(exc)}
            resp.status = falcon.HTTP_503
            return

        resp.media = result
        resp.status = falcon.HTTP_200