"""Cities catalog data access layer."""

from typing import Optional

from psycopg import connect


class CitiesStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_cities(
        self, country_code: Optional[str] = None, region_id: Optional[str] = None, limit: int = 500
    ) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if country_code and region_id:
                    cur.execute(
                        """
                        SELECT id, country_code, region_id, name, normalized_name, created_at, updated_at
                        FROM cities
                        WHERE country_code = %s AND region_id = %s
                        ORDER BY name ASC
                        LIMIT %s
                        """,
                        (country_code.upper(), region_id, limit),
                    )
                elif country_code:
                    cur.execute(
                        """
                        SELECT id, country_code, region_id, name, normalized_name, created_at, updated_at
                        FROM cities
                        WHERE country_code = %s
                        ORDER BY name ASC
                        LIMIT %s
                        """,
                        (country_code.upper(), limit),
                    )
                elif region_id:
                    cur.execute(
                        """
                        SELECT id, country_code, region_id, name, normalized_name, created_at, updated_at
                        FROM cities
                        WHERE region_id = %s
                        ORDER BY name ASC
                        LIMIT %s
                        """,
                        (region_id, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, country_code, region_id, name, normalized_name, created_at, updated_at
                        FROM cities
                        ORDER BY country_code ASC, name ASC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
