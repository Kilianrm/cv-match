"""Regions catalog data access layer."""

from typing import Optional

from psycopg import connect


class RegionsStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_regions(self, country_code: Optional[str] = None, limit: int = 500) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if country_code:
                    cur.execute(
                        """
                        SELECT id, country_code, name, normalized_name, code, created_at, updated_at
                        FROM regions
                        WHERE country_code = %s
                        ORDER BY name ASC
                        LIMIT %s
                        """,
                        (country_code.upper(), limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, country_code, name, normalized_name, code, created_at, updated_at
                        FROM regions
                        ORDER BY country_code ASC, name ASC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
