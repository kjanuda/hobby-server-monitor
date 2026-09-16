from db.database import get_connection


class AuditRepository:
    def create_log(
        self,
        action,
        user_id=None,
        container_id=None,
        actor_email=None,
        details=None,
    ):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO audit_logs (
                    user_id,
                    container_id,
                    actor_email,
                    action,
                    details
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    container_id,
                    actor_email,
                    action,
                    details,
                ),
            )

            connection.commit()

            row = connection.execute(
                """
                SELECT *
                FROM audit_logs
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def list_logs(self, limit=100):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()