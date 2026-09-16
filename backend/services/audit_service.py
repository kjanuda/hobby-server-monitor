import json

from repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self):
        self.repository = AuditRepository()

    def log(
        self,
        action,
        actor_email=None,
        user_id=None,
        container_id=None,
        details=None,
    ):
        serialized_details = None

        if details is not None:
            serialized_details = json.dumps(
                details,
                separators=(",", ":"),
                sort_keys=True,
            )

        return self.repository.create_log(
            action=action,
            user_id=user_id,
            container_id=container_id,
            actor_email=actor_email,
            details=serialized_details,
        )

    def list_logs(self, limit=100):
        if not isinstance(limit, int):
            raise ValueError("Limit must be an integer.")

        if limit < 1 or limit > 500:
            raise ValueError(
                "Limit must be between 1 and 500."
            )

        return self.repository.list_logs(limit)