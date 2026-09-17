import hmac

import falcon

from config import CSRF_COOKIE_NAME


class CSRFMiddleware:
    SAFE_METHODS = {
        "GET",
        "HEAD",
        "OPTIONS",
    }

    def process_request(
        self,
        req,
        resp,
    ):
        if req.method in self.SAFE_METHODS:
            return

        cookie_token = req.cookies.get(
            CSRF_COOKIE_NAME
        )

        header_token = req.get_header(
            "X-CSRF-Token"
        )

        if (
            not cookie_token
            or not header_token
            or not hmac.compare_digest(
                cookie_token,
                header_token,
            )
        ):
            raise falcon.HTTPForbidden(
                title="CSRF validation failed",
                description=(
                    "A valid CSRF token is required "
                    "for this request."
                ),
            )