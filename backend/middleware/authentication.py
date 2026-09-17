import falcon

from config import SESSION_COOKIE_NAME
from services.session_service import SessionService


class AuthenticationMiddleware:
    PUBLIC_PATHS = {
        "/api/health",
        "/api/auth/google/login",
        "/api/auth/google/callback",
        "/api/auth/me",
        "/api/auth/logout",
    }

    def __init__(self):
        self.session_service = SessionService()

    def process_request(self, req, resp):
        if req.path in self.PUBLIC_PATHS:
            return

        raw_token = req.cookies.get(
            SESSION_COOKIE_NAME
        )

        if not raw_token:
            raise falcon.HTTPUnauthorized(
                title="Authentication required",
                description=(
                    "A valid authenticated session is required."
                ),
            )

        user = self.session_service.get_user_from_token(
            raw_token
        )

        if not user:
            raise falcon.HTTPUnauthorized(
                title="Invalid session",
                description=(
                    "The session is invalid, expired, "
                    "or the user no longer has access."
                ),
            )

        req.context.user = user