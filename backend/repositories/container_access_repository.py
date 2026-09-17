from db.database import get_connection


class ContainerAccessRepository:
    def assign(self, user_id, container_id):
        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT OR IGNORE INTO container_access (
                    user_id,
                    container_id
                )
                VALUES (?, ?)
                """,
                (user_id, container_id),
            )

            connection.commit()

        finally:
            connection.close()

    def revoke(self, user_id, container_id):
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM container_access
                WHERE user_id = ?
                  AND container_id = ?
                """,
                (user_id, container_id),
            )

            connection.commit()

        finally:
            connection.close()

    def has_access(self, user_id, container_id):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT 1
                FROM container_access
                WHERE user_id = ?
                  AND container_id = ?
                """,
                (user_id, container_id),
            ).fetchone()

            return row is not None

        finally:
            connection.close()

    def list_for_user(self, user_id):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT containers.*
                FROM containers
                JOIN container_access
                  ON container_access.container_id
                   = containers.id
                WHERE container_access.user_id = ?
                ORDER BY containers.lxd_name ASC
                """,
                (user_id,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()