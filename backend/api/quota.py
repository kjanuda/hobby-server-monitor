import falcon

from services.quota_service import (
    QuotaService,
    QuotaValidationError,
)


class MyQuotaResource:
    def __init__(self):
        self.quota_service = QuotaService()

    def on_get(self, req, resp):
        user = req.context.user

        try:
            summary = (
                self.quota_service
                .get_user_quota_summary(
                    user["id"]
                )
            )

        except QuotaValidationError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_503
            return

        resp.media = summary
        resp.status = falcon.HTTP_200