from db.database import get_connection


class OAuthStateRepository:
    def create_state(
        self,
        state_hash,
        code_verifier,
        expires_at,
    ):
        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO oauth_states (
                    state_hash,
                    code_verifier,
                    expires_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    state_hash,
                    code_verifier,
                    expires_at,
                ),
            )

            connection.commit()

        finally:
            connection.close()

    def consume_state(
        self,
        state_hash,
        current_time,
    ):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM oauth_states
                WHERE state_hash = ?
                  AND expires_at > ?
                """,
                (
                    state_hash,
                    current_time,
                ),
            ).fetchone()

            connection.execute(
                """
                DELETE FROM oauth_states
                WHERE state_hash = ?
                """,
                (state_hash,),
            )

            connection.commit()

            return dict(row) if row else None

        finally:
            connection.close()