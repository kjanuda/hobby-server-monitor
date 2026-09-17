import re
import sqlite3

from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.session_service import SessionService


class UserValidationError(Exception):
    pass


class UserNotFoundError(UserValidationError):
    pass


class UserOperationForbiddenError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class GoogleIdentityError(Exception):
    pass


class UserService:
    VALID_ROLES = {"admin", "container_user"}

    def __init__(self):
        self.repository = UserRepository()
        self.audit_service = AuditService()
        self.session_service = SessionService()

    def create_user(
        self,
        email,
        name=None,
        role="container_user",
        ram_quota_bytes=0,
        cpu_quota=0,
        disk_quota_bytes=0,
        actor_email=None,
    ):
        email = self._validate_email(email)
        role = self._validate_role(role)

        self._validate_quota(
            "RAM quota",
            ram_quota_bytes,
        )

        self._validate_quota(
            "CPU quota",
            cpu_quota,
        )

        self._validate_quota(
            "Disk quota",
            disk_quota_bytes,
        )

        try:
            user = self.repository.create_user(
                email=email,
                name=name,
                role=role,
                ram_quota_bytes=ram_quota_bytes,
                cpu_quota=cpu_quota,
                disk_quota_bytes=disk_quota_bytes,
            )

            self.audit_service.log(
                action="user.created",
                actor_email=actor_email,
                user_id=user["id"],
                details={
                    "email": user["email"],
                    "role": user["role"],
                },
            )

            return user

        except sqlite3.IntegrityError as exc:
            if "users.email" in str(exc):
                raise UserAlreadyExistsError(
                    f"A user with email '{email}' already exists."
                ) from exc

            raise

    def get_user_by_email(self, email):
        email = self._validate_email(email)

        return self.repository.get_user_by_email(email)

    def get_user_by_google_sub(self, google_sub):
        if not isinstance(google_sub, str):
            raise GoogleIdentityError(
                "Google subject must be a string."
            )

        google_sub = google_sub.strip()

        if not google_sub:
            raise GoogleIdentityError(
                "Google subject cannot be empty."
            )

        return self.repository.get_user_by_google_sub(
            google_sub
        )

    def bind_google_identity(
        self,
        user_id,
        google_sub,
        name=None,
    ):
        if not isinstance(google_sub, str):
            raise GoogleIdentityError(
                "Google subject must be a string."
            )

        google_sub = google_sub.strip()

        if not google_sub:
            raise GoogleIdentityError(
                "Google subject cannot be empty."
            )

        existing_user = self.repository.get_user_by_id(
            user_id
        )

        if not existing_user:
            raise UserValidationError(
                "User not found."
            )

        linked_user = self.repository.get_user_by_google_sub(
            google_sub
        )

        if linked_user and linked_user["id"] != user_id:
            raise GoogleIdentityError(
                "This Google account is already linked "
                "to another user."
            )

        try:
            user = self.repository.bind_google_identity(
                user_id=user_id,
                google_sub=google_sub,
                name=name,
            )

        except sqlite3.IntegrityError as exc:
            raise GoogleIdentityError(
                "Unable to link this Google account."
            ) from exc

        self.audit_service.log(
            action="user.google_identity_bound",
            user_id=user_id,
            details={
                "email": user["email"],
            },
        )

        return user

    def authenticate_google_identity(self, profile):
        email = profile.get("email")
        google_sub = profile.get("sub")
        email_verified = profile.get("email_verified")
        name = profile.get("name")

        if not email or not google_sub:
            raise GoogleIdentityError(
                "Google did not return the required identity fields."
            )

        if email_verified is not True:
            raise GoogleIdentityError(
                "Google email address is not verified."
            )

        if not isinstance(email, str):
            raise GoogleIdentityError(
                "Google email must be a string."
            )

        if not isinstance(google_sub, str):
            raise GoogleIdentityError(
                "Google subject must be a string."
            )

        email = email.strip().lower()
        google_sub = google_sub.strip()

        if not email or not google_sub:
            raise GoogleIdentityError(
                "Google did not return the required identity fields."
            )

        user = self.repository.get_user_by_email(email)

        # Invite-only access.
        if not user:
            raise GoogleIdentityError(
                "This Google account has not been invited."
            )

        if not user["invited"]:
            raise GoogleIdentityError(
                "This Google account has not been invited."
            )

        if not user["active"]:
            raise GoogleIdentityError(
                "This user account has been revoked."
            )

        existing_google_user = (
            self.repository.get_user_by_google_sub(
                google_sub
            )
        )

        if (
            existing_google_user
            and existing_google_user["id"] != user["id"]
        ):
            raise GoogleIdentityError(
                "This Google identity is already linked "
                "to another account."
            )

        # Existing Google identity is already linked.
        if user["google_sub"]:
            if user["google_sub"] != google_sub:
                raise GoogleIdentityError(
                    "Google identity does not match "
                    "the account previously linked."
                )

            return user

        # First successful login:
        # bind this Google identity to the invited user.
        return self.repository.bind_google_identity(
            user_id=user["id"],
            google_sub=google_sub,
            name=name,
        )

    def list_users(self):
        return self.repository.list_users()

    def _validate_email(self, email):
        if not isinstance(email, str):
            raise UserValidationError(
                "Email must be a string."
            )

        email = email.strip().lower()

        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

        if not re.match(pattern, email):
            raise UserValidationError(
                "Invalid email address."
            )

        return email

    def _validate_role(self, role):
        if role not in self.VALID_ROLES:
            raise UserValidationError(
                "Role must be 'admin' or 'container_user'."
            )

        return role

    def _validate_quota(self, name, value):
        if not isinstance(value, int):
            raise UserValidationError(
                f"{name} must be an integer."
            )

        if value < 0:
            raise UserValidationError(
                f"{name} cannot be negative."
            )

    def get_user_by_id(self, user_id):
        user = self.repository.get_user_by_id(
            user_id
        )

        if not user:
            raise UserNotFoundError(
                "User not found."
            )

        return user

    def update_user(
        self,
        user_id,
        name,
        role,
        ram_quota_bytes,
        cpu_quota,
        disk_quota_bytes,
        actor_user_id=None,
        actor_email=None,
    ):
        existing_user = self.repository.get_user_by_id(
            user_id
        )

        if not existing_user:
            raise UserNotFoundError(
                "User not found."
            )

        role = self._validate_role(role)

        self._validate_quota(
            "RAM quota",
            ram_quota_bytes,
        )

        self._validate_quota(
            "CPU quota",
            cpu_quota,
        )

        self._validate_quota(
            "Disk quota",
            disk_quota_bytes,
        )

        if (
            actor_user_id == user_id
            and role != "admin"
        ):
            raise UserOperationForbiddenError(
                "Administrators cannot demote themselves."
            )

        updated_user = self.repository.update_user(
            user_id=user_id,
            name=name,
            role=role,
            ram_quota_bytes=ram_quota_bytes,
            cpu_quota=cpu_quota,
            disk_quota_bytes=disk_quota_bytes,
        )

        self.audit_service.log(
            action="user.updated",
            actor_email=actor_email,
            user_id=user_id,
            details={
                "before": {
                    "role": existing_user["role"],
                    "ram_quota_bytes": existing_user[
                        "ram_quota_bytes"
                    ],
                    "cpu_quota": existing_user[
                        "cpu_quota"
                    ],
                    "disk_quota_bytes": existing_user[
                        "disk_quota_bytes"
                    ],
                },
                "after": {
                    "role": updated_user["role"],
                    "ram_quota_bytes": updated_user[
                        "ram_quota_bytes"
                    ],
                    "cpu_quota": updated_user[
                        "cpu_quota"
                    ],
                    "disk_quota_bytes": updated_user[
                        "disk_quota_bytes"
                    ],
                },
            },
        )

        return updated_user

    def revoke_user(
        self,
        user_id,
        actor_user_id=None,
        actor_email=None,
    ):
        existing_user = self.repository.get_user_by_id(
            user_id
        )

        if not existing_user:
            raise UserNotFoundError(
                "User not found."
            )

        if actor_user_id == user_id:
            raise UserOperationForbiddenError(
                "Administrators cannot revoke themselves."
            )

        if not existing_user["active"]:
            raise UserValidationError(
                "User is already revoked."
            )

        revoked_user = self.repository.revoke_user(
            user_id
        )

        self.session_service.revoke_all_user_sessions(
            user_id
        )

        self.audit_service.log(
            action="user.revoked",
            actor_email=actor_email,
            user_id=user_id,
            details={
                "email": revoked_user["email"],
                "role": revoked_user["role"],
            },
        )

        return revoked_user