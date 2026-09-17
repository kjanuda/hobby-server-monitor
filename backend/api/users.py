import falcon

from services.authorization import require_admin
from services.user_service import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserOperationForbiddenError,
    UserService,
    UserValidationError,
)


class UsersResource:
    def __init__(self):
        self.user_service = UserService()

    @falcon.before(require_admin)
    def on_get(self, req, resp):
        users = self.user_service.list_users()

        resp.media = {
            "users": [
                self._serialize_user(user)
                for user in users
            ],
            "count": len(users),
        }

        resp.status = falcon.HTTP_200

    @falcon.before(require_admin)
    def on_post(self, req, resp):
        data = req.media or {}

        email = data.get("email")

        if not email:
            resp.media = {
                "error": "Email is required."
            }
            resp.status = falcon.HTTP_400
            return

        try:
            user = self.user_service.create_user(
                email=email,
                name=data.get("name"),
                role=data.get(
                    "role",
                    "container_user",
                ),
                ram_quota_bytes=data.get(
                    "ram_quota_bytes",
                    0,
                ),
                cpu_quota=data.get(
                    "cpu_quota",
                    0,
                ),
                disk_quota_bytes=data.get(
                    "disk_quota_bytes",
                    0,
                ),
                actor_email=req.context.user["email"],
            )

        except UserAlreadyExistsError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_409
            return

        except UserValidationError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": "User invited successfully.",
            "user": self._serialize_user(user),
        }

        resp.status = falcon.HTTP_201

    @staticmethod
    def _serialize_user(user):
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "invited": bool(user["invited"]),
            "active": bool(user["active"]),
            "ram_quota_bytes": user[
                "ram_quota_bytes"
            ],
            "cpu_quota": user["cpu_quota"],
            "disk_quota_bytes": user[
                "disk_quota_bytes"
            ],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
        }


class UserResource:
    ALLOWED_UPDATE_FIELDS = {
        "name",
        "role",
        "ram_quota_bytes",
        "cpu_quota",
        "disk_quota_bytes",
    }

    def __init__(self):
        self.user_service = UserService()

    @falcon.before(require_admin)
    def on_patch(self, req, resp, user_id):
        data = req.media or {}

        unknown_fields = (
            set(data.keys())
            - self.ALLOWED_UPDATE_FIELDS
        )

        if unknown_fields:
            resp.media = {
                "error": (
                    "Unknown fields: "
                    + ", ".join(
                        sorted(unknown_fields)
                    )
                )
            }
            resp.status = falcon.HTTP_400
            return

        if not data:
            resp.media = {
                "error": (
                    "At least one field must be provided."
                )
            }
            resp.status = falcon.HTTP_400
            return

        try:
            existing = (
                self.user_service.get_user_by_id(
                    user_id
                )
            )

            updated_user = (
                self.user_service.update_user(
                    user_id=user_id,
                    name=data.get(
                        "name",
                        existing["name"],
                    ),
                    role=data.get(
                        "role",
                        existing["role"],
                    ),
                    ram_quota_bytes=data.get(
                        "ram_quota_bytes",
                        existing[
                            "ram_quota_bytes"
                        ],
                    ),
                    cpu_quota=data.get(
                        "cpu_quota",
                        existing["cpu_quota"],
                    ),
                    disk_quota_bytes=data.get(
                        "disk_quota_bytes",
                        existing[
                            "disk_quota_bytes"
                        ],
                    ),
                    actor_user_id=(
                        req.context.user["id"]
                    ),
                    actor_email=(
                        req.context.user["email"]
                    ),
                )
            )

        except UserNotFoundError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_404
            return

        except UserOperationForbiddenError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_403
            return

        except UserValidationError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": "User updated successfully.",
            "user": UsersResource._serialize_user(
                updated_user
            ),
        }

        resp.status = falcon.HTTP_200

    @falcon.before(require_admin)
    def on_delete(self, req, resp, user_id):
        try:
            revoked_user = (
                self.user_service.revoke_user(
                    user_id=user_id,
                    actor_user_id=(
                        req.context.user["id"]
                    ),
                    actor_email=(
                        req.context.user["email"]
                    ),
                )
            )

        except UserNotFoundError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_404
            return

        except UserOperationForbiddenError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_403
            return

        except UserValidationError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": "User access revoked.",
            "user": UsersResource._serialize_user(
                revoked_user
            ),
        }

        resp.status = falcon.HTTP_200