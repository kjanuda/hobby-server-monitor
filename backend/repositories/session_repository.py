from db.database import get_connection


class SessionRepository:
    def create_session(
        self,
        token_hash,
        user_id,
        expires_at,
    ):
        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO sessions (
                    token_hash,
                    user_id,
                    expires_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    token_hash,
                    user_id,
                    expires_at,
                ),
            )

            connection.commit()

        finally:
            connection.close()

    def get_user_by_token_hash(
        self,
        token_hash,
        current_time,
    ):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT
                    users.id,
                    users.email,
                    users.name,
                    users.google_sub,
                    users.role,
                    users.invited,
                    users.active,
                    users.ram_quota_bytes,
                    users.cpu_quota,
                    users.disk_quota_bytes,
                    sessions.expires_at
                FROM sessions
                JOIN users
                    ON users.id = sessions.user_id
                WHERE sessions.token_hash = ?
                  AND sessions.expires_at > ?
                  AND users.active = 1
                  AND users.invited = 1
                """,
                (
                    token_hash,
                    current_time,
                ),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def delete_session(self, token_hash):
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE token_hash = ?
                """,
                (token_hash,),
            )

            connection.commit()

        finally:
            connection.close()

    def delete_user_sessions(self, user_id):
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE user_id = ?
                """,
                (user_id,),
            )

            connection.commit()

        finally:
            connection.close()

    def delete_expired_sessions(self, current_time):
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE expires_at <= ?
                """,
                (current_time,),
            )

            connection.commit()

        finally:
            connection.close()