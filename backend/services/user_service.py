import re
import sqlite3

from repositories.user_repository import UserRepository


class UserValidationError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class UserService:
    VALID_ROLES = {"admin", "container_user"}

    def __init__(self):
        self.repository = UserRepository()

    def create_user(
        self,
        email,
        name=None,
        role="container_user",
        ram_quota_bytes=0,
        cpu_quota=0,
        disk_quota_bytes=0,
    ):
        email = self._validate_email(email)
        role = self._validate_role(role)

        self._validate_quota("RAM quota", ram_quota_bytes)
        self._validate_quota("CPU quota", cpu_quota)
        self._validate_quota("Disk quota", disk_quota_bytes)

        try:
            return self.repository.create_user(
                email=email,
                name=name,
                role=role,
                ram_quota_bytes=ram_quota_bytes,
                cpu_quota=cpu_quota,
                disk_quota_bytes=disk_quota_bytes,
            )

        except sqlite3.IntegrityError as exc:
            if "users.email" in str(exc):
                raise UserAlreadyExistsError(
                    f"A user with email '{email}' already exists."
                ) from exc

            raise

    def get_user_by_email(self, email):
        email = self._validate_email(email)
        return self.repository.get_user_by_email(email)

    def list_users(self):
        return self.repository.list_users()

    def _validate_email(self, email):
        if not isinstance(email, str):
            raise UserValidationError("Email must be a string.")

        email = email.strip().lower()

        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

        if not re.match(pattern, email):
            raise UserValidationError("Invalid email address.")

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