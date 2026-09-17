import shlex

from repositories.container_repository import ContainerRepository
from services.audit_service import AuditService
from services.container_access_service import (
    ContainerAccessForbiddenError,
    ContainerAccessService,
)
from services.lxd_service import LXDService


class TerminalValidationError(Exception):
    pass


class TerminalContainerNotFoundError(Exception):
    pass


class TerminalStateError(Exception):
    pass


class TerminalSecurityError(Exception):
    pass


class TerminalExecutionError(Exception):
    pass


class TerminalService:
    MAX_COMMAND_LENGTH = 1024
    MAX_OUTPUT_BYTES = 64 * 1024
    COMMAND_TIMEOUT_SECONDS = 10

    def __init__(self):
        self.container_repository = ContainerRepository()
        self.access_service = ContainerAccessService()
        self.lxd_service = LXDService()
        self.audit_service = AuditService()

    def execute(
        self,
        user,
        container_id,
        command,
    ):
        # Access check FIRST.
        self.access_service.assert_user_access(
            user,
            container_id,
        )

        record = self.container_repository.get_by_id(
            container_id
        )

        if not record:
            raise TerminalContainerNotFoundError(
                "Container not found."
            )

        argv = self._parse_command(command)

        try:
            container = (
                self.lxd_service.client
                .containers.get(record["lxd_name"])
            )

        except Exception as exc:
            raise TerminalExecutionError(
                "Container is unavailable in LXD."
            ) from exc

        if container.status != "Running":
            raise TerminalStateError(
                "Container must be running."
            )

        config = container.expanded_config or {}

        if (
            str(
                config.get(
                    "security.privileged",
                    "false",
                )
            ).lower()
            == "true"
        ):
            raise TerminalSecurityError(
                "Terminal access is disabled "
                "for privileged containers."
            )

        # Execute directly inside container.
        # No host shell and no shell interpolation.
        command_argv = [
            "/usr/bin/timeout",
            f"{self.COMMAND_TIMEOUT_SECONDS}s",
            *argv,
        ]

        try:
            result = container.execute(
                command_argv
            )

        except Exception as exc:
            raise TerminalExecutionError(
                "Unable to execute command "
                "inside the container."
            ) from exc

        stdout, stdout_truncated = self._truncate(
            result.stdout or ""
        )

        stderr, stderr_truncated = self._truncate(
            result.stderr or ""
        )

        truncated = (
            stdout_truncated
            or stderr_truncated
        )

        # Do not log the complete command.
        # Arguments could contain passwords/tokens.
        self.audit_service.log(
            action="container.terminal_exec",
            actor_email=user["email"],
            user_id=user["id"],
            container_id=container_id,
            details={
                "container": record["lxd_name"],
                "executable": argv[0],
                "exit_code": result.exit_code,
                "output_truncated": truncated,
            },
        )

        return {
            "exit_code": result.exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated,
        }

    def _parse_command(self, command):
        if not isinstance(command, str):
            raise TerminalValidationError(
                "Command must be a string."
            )

        command = command.strip()

        if not command:
            raise TerminalValidationError(
                "Command cannot be empty."
            )

        if len(command) > self.MAX_COMMAND_LENGTH:
            raise TerminalValidationError(
                "Command is too long."
            )

        try:
            argv = shlex.split(command)

        except ValueError as exc:
            raise TerminalValidationError(
                "Invalid command syntax."
            ) from exc

        if not argv:
            raise TerminalValidationError(
                "Command cannot be empty."
            )

        return argv

    def _truncate(self, value):
        encoded = value.encode(
            "utf-8",
            errors="replace",
        )

        if len(encoded) <= self.MAX_OUTPUT_BYTES:
            return value, False

        truncated = encoded[
            :self.MAX_OUTPUT_BYTES
        ].decode(
            "utf-8",
            errors="replace",
        )

        return truncated, True