import falcon

from services.container_access_service import (
    ContainerAccessForbiddenError,
    ContainerAccessService,
)
from services.metrics_query_service import (
    MetricsQueryError,
    MetricsQueryService,
)


class ContainerMetricsResource:
    def __init__(self):
        self.query_service = MetricsQueryService()
        self.access_service = (
            ContainerAccessService()
        )

    def on_get(
        self,
        req,
        resp,
        container_id,
    ):
        user = req.context.user

        try:
            self.access_service.assert_user_access(
                user,
                container_id,
            )

        except ContainerAccessForbiddenError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_403
            return

        try:
            hours = req.get_param_as_int(
                "hours"
            )

            max_points = req.get_param_as_int(
                "max_points"
            )

            result = (
                self.query_service.get_history(
                    container_id=container_id,
                    hours=hours or 24,
                    max_points=max_points or 360,
                )
            )

        except (
            MetricsQueryError,
            falcon.HTTPInvalidParam,
        ) as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = result
        resp.status = falcon.HTTP_200