"""Degree types catalog data access layer."""

from typing import Optional

from psycopg import connect


class DegreeTypesStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_degree_types(self, q: Optional[str] = None, limit: int = 200) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if q:
                    cur.execute(
                        """
                        SELECT id, degree_name, normalized_degree, level, created_at, updated_at
                        FROM degree_types
                        WHERE normalized_degree LIKE %s
                        ORDER BY level ASC NULLS LAST, degree_name ASC
                        LIMIT %s
                        """,
                        (f"%{' '.join(q.lower().split())}%", limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, degree_name, normalized_degree, level, created_at, updated_at
                        FROM degree_types
                        ORDER BY level ASC NULLS LAST, degree_name ASC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
