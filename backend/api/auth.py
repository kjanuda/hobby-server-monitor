import secrets

import falcon

from authlib.integrations.requests_client import OAuth2Session

from config import (
    CSRF_COOKIE_NAME,
    GOOGLE_AUTHORIZATION_ENDPOINT,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_ENDPOINT,
    GOOGLE_USERINFO_ENDPOINT,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_SECONDS,
)
from services.oauth_state_service import OAuthStateService
from services.session_service import SessionService
from services.user_service import (
    GoogleIdentityError,
    UserService,
)


def set_csrf_cookie(resp):
    csrf_token = secrets.token_urlsafe(
        32
    )

    resp.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        http_only=False,
        same_site="Lax",
    )

    return csrf_token


class GoogleLoginResource:
    def __init__(self):
        self.state_service = OAuthStateService()

    def on_get(self, req, resp):
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            resp.media = {
                "error": "Google OAuth is not configured."
            }
            resp.status = falcon.HTTP_503
            return

        state, code_verifier = (
            self.state_service.create_state()
        )

        client = OAuth2Session(
            GOOGLE_CLIENT_ID,
            GOOGLE_CLIENT_SECRET,
            scope="openid email profile",
            redirect_uri=GOOGLE_REDIRECT_URI,
            code_challenge_method="S256",
        )

        authorization_url, _ = (
            client.create_authorization_url(
                GOOGLE_AUTHORIZATION_ENDPOINT,
                state=state,
                code_verifier=code_verifier,
                prompt="select_account",
            )
        )

        resp.status = falcon.HTTP_302
        resp.location = authorization_url


class GoogleCallbackResource:
    def __init__(self):
        self.state_service = OAuthStateService()
        self.user_service = UserService()
        self.session_service = SessionService()

    def on_get(self, req, resp):
        oauth_error = req.get_param("error")

        if oauth_error:
            resp.media = {
                "error": "Google authorization was denied.",
                "details": oauth_error,
            }
            resp.status = falcon.HTTP_400
            return

        code = req.get_param("code")
        state = req.get_param("state")

        if not code or not state:
            resp.media = {
                "error": "Missing OAuth code or state."
            }
            resp.status = falcon.HTTP_400
            return

        stored_state = (
            self.state_service.consume_state(state)
        )

        if not stored_state:
            resp.media = {
                "error": (
                    "Invalid or expired OAuth state."
                )
            }
            resp.status = falcon.HTTP_400
            return

        try:
            client = OAuth2Session(
                GOOGLE_CLIENT_ID,
                GOOGLE_CLIENT_SECRET,
                scope="openid email profile",
                redirect_uri=GOOGLE_REDIRECT_URI,
                state=state,
                code_challenge_method="S256",
            )

            client.fetch_token(
                GOOGLE_TOKEN_ENDPOINT,
                code=code,
                code_verifier=stored_state[
                    "code_verifier"
                ],
            )

            userinfo_response = client.get(
                GOOGLE_USERINFO_ENDPOINT
            )

            userinfo_response.raise_for_status()

            profile = userinfo_response.json()

            user = (
                self.user_service
                .authenticate_google_identity(
                    profile
                )
            )

            session_token = (
                self.session_service.create_session(
                    user["id"]
                )
            )

        except GoogleIdentityError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_403
            return

        except Exception:
            resp.media = {
                "error": (
                    "Google authentication failed."
                )
            }
            resp.status = falcon.HTTP_502
            return

        resp.set_cookie(
            SESSION_COOKIE_NAME,
            session_token,
            max_age=SESSION_TTL_SECONDS,
            path="/",
            secure=SESSION_COOKIE_SECURE,
            http_only=True,
            same_site="Lax",
        )

        set_csrf_cookie(resp)

        resp.status = falcon.HTTP_302
        resp.location = "/"


class CurrentUserResource:
    def __init__(self):
        self.session_service = SessionService()

    def on_get(self, req, resp):
        raw_token = req.cookies.get(
            SESSION_COOKIE_NAME
        )

        user = (
            self.session_service
            .get_user_from_token(raw_token)
        )

        if not user:
            resp.media = {
                "authenticated": False
            }
            resp.status = falcon.HTTP_401
            return

        csrf_token = req.cookies.get(
            CSRF_COOKIE_NAME
        )

        if not csrf_token:
            csrf_token = set_csrf_cookie(
                resp
            )

        resp.media = {
            "authenticated": True,
            "csrf_token": csrf_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "ram_quota_bytes": (
                    user["ram_quota_bytes"]
                ),
                "cpu_quota": user["cpu_quota"],
                "disk_quota_bytes": (
                    user["disk_quota_bytes"]
                ),
            },
        }

        resp.status = falcon.HTTP_200


class LogoutResource:
    def __init__(self):
        self.session_service = SessionService()

    def on_post(self, req, resp):
        raw_token = req.cookies.get(
            SESSION_COOKIE_NAME
        )

        self.session_service.delete_session(
            raw_token
        )

        resp.unset_cookie(
            SESSION_COOKIE_NAME,
            path="/",
            same_site="Lax",
        )

        resp.unset_cookie(
            CSRF_COOKIE_NAME,
            path="/",
            same_site="Lax",
        )

        resp.media = {
            "message": "Logged out successfully."
        }

        resp.status = falcon.HTTP_200