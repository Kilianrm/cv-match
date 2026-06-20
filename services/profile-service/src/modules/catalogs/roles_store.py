"""Roles catalog data access layer."""

from typing import Optional

from psycopg import connect


class RolesStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_roles(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if q and category:
                    cur.execute(
                        """
                        SELECT id, role_name, normalized_role, category, created_at, updated_at
                        FROM roles
                        WHERE category = %s AND normalized_role LIKE %s
                        ORDER BY role_name ASC
                        LIMIT %s
                        """,
                        (category, f"%{' '.join(q.lower().split())}%", limit),
                    )
                elif q:
                    cur.execute(
                        """
                        SELECT id, role_name, normalized_role, category, created_at, updated_at
                        FROM roles
                        WHERE normalized_role LIKE %s
                        ORDER BY role_name ASC
                        LIMIT %s
                        """,
                        (f"%{' '.join(q.lower().split())}%", limit),
                    )
                elif category:
                    cur.execute(
                        """
                        SELECT id, role_name, normalized_role, category, created_at, updated_at
                        FROM roles
                        WHERE category = %s
                        ORDER BY role_name ASC
                        LIMIT %s
                        """,
                        (category, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, role_name, normalized_role, category, created_at, updated_at
                        FROM roles
                        ORDER BY role_name ASC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
