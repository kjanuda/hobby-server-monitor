from db.database import get_connection


class UserRepository:
    def create_user(
        self,
        email,
        name=None,
        role="container_user",
        ram_quota_bytes=0,
        cpu_quota=0,
        disk_quota_bytes=0,
    ):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    email,
                    name,
                    role,
                    invited,
                    active,
                    ram_quota_bytes,
                    cpu_quota,
                    disk_quota_bytes
                )
                VALUES (?, ?, ?, 1, 1, ?, ?, ?)
                """,
                (
                    email,
                    name,
                    role,
                    ram_quota_bytes,
                    cpu_quota,
                    disk_quota_bytes,
                ),
            )

            connection.commit()

            return self.get_user_by_id(
                cursor.lastrowid,
                connection=connection,
            )

        finally:
            connection.close()

    def get_user_by_id(self, user_id, connection=None):
        owns_connection = connection is None

        if connection is None:
            connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            if owns_connection:
                connection.close()

    def get_user_by_email(self, email):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_user_by_google_sub(self, google_sub):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE google_sub = ?
                """,
                (google_sub,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def bind_google_identity(
        self,
        user_id,
        google_sub,
        name=None,
    ):
        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE users
                SET
                    google_sub = ?,
                    name = COALESCE(?, name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    google_sub,
                    name,
                    user_id,
                ),
            )

            connection.commit()

            return self.get_user_by_id(
                user_id,
                connection=connection,
            )

        finally:
            connection.close()

    def list_users(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM users
                ORDER BY id ASC
                """
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def update_user(
        self,
        user_id,
        name,
        role,
        ram_quota_bytes,
        cpu_quota,
        disk_quota_bytes,
    ):
        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE users
                SET
                    name = ?,
                    role = ?,
                    ram_quota_bytes = ?,
                    cpu_quota = ?,
                    disk_quota_bytes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    name,
                    role,
                    ram_quota_bytes,
                    cpu_quota,
                    disk_quota_bytes,
                    user_id,
                ),
            )

            connection.commit()

            return self.get_user_by_id(
                user_id,
                connection=connection,
            )

        finally:
            connection.close()

    def revoke_user(self, user_id):
        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE users
                SET
                    active = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (user_id,),
            )

            connection.commit()

            return self.get_user_by_id(
                user_id,
                connection=connection,
            )

        finally:
            connection.close()