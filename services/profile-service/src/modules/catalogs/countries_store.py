"""Countries catalog data access layer."""

from psycopg import connect


class CountriesStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_countries(self, limit: int = 500) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT code, name, normalized_name, created_at, updated_at
                    FROM countries
                    ORDER BY name ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
