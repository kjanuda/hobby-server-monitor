from db.database import get_connection


class ContainerRepository:
    def upsert_container(
        self,
        lxd_uuid,
        lxd_name,
        description=None,
    ):
        connection = get_connection()

        try:
            existing = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE lxd_uuid = ?
                """,
                (lxd_uuid,),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE containers
                    SET
                        lxd_name = ?,
                        description = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE lxd_uuid = ?
                    """,
                    (
                        lxd_name,
                        description,
                        lxd_uuid,
                    ),
                )

            else:
                connection.execute(
                    """
                    INSERT INTO containers (
                        lxd_uuid,
                        lxd_name,
                        description
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        lxd_uuid,
                        lxd_name,
                        description,
                    ),
                )

            connection.commit()

            row = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE lxd_uuid = ?
                """,
                (lxd_uuid,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_by_id(self, container_id):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE id = ?
                """,
                (container_id,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_by_lxd_uuid(self, lxd_uuid):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE lxd_uuid = ?
                """,
                (lxd_uuid,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_by_lxd_name(self, lxd_name):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM containers
                WHERE lxd_name = ?
                """,
                (lxd_name,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def list_all(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM containers
                ORDER BY lxd_name ASC
                """
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def set_owner(
        self,
        container_id,
        owner_user_id,
    ):
        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE containers
                SET
                    owner_user_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    owner_user_id,
                    container_id,
                ),
            )

            connection.commit()

            return self.get_by_id(container_id)

        finally:
            connection.close()

    def delete_by_id(self, container_id):
        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM containers
                WHERE id = ?
                """,
                (container_id,),
            )

            connection.commit()

        finally:
            connection.close()