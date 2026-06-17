
"""Location data access layer for countries, regions, and cities."""

from typing import Optional
from psycopg import connect


class LocationsStore:
    """Query interface for location reference tables."""

    def __init__(self, database_url: str):
        """Initialize store with database connection string."""
        self.database_url = database_url

    def _get_connection(self):
        """Create and return a database connection."""
        return connect(self.database_url)

    def _as_dict(self, record):
        """Convert tuple record to dict with column names."""
        # For psycopg.Connection.cursor(), we need to map manually
        # Instead, we'll return the raw tuples and handle mapping in methods
        return record
    def get_countries(self, limit: int = 500) -> list[dict]:
        """Fetch all countries, optionally limited.
        
        Args:
            limit: Maximum number of countries to return (default 500).
            
        Returns:
            List of dictionaries with keys: code, name, normalized_name, created_at, updated_at
        """
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

    def get_regions(self, country_code: Optional[str] = None, limit: int = 500) -> list[dict]:
        """Fetch regions, optionally filtered by country code.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code to filter by (optional).
            limit: Maximum number of regions to return (default 500).
            
        Returns:
            List of dictionaries with keys: id, country_code, name, normalized_name, code, created_at, updated_at
        """
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

    def get_cities(
        self, country_code: Optional[str] = None, region_id: Optional[str] = None, limit: int = 500
    ) -> list[dict]:
        """Fetch cities, optionally filtered by country code and/or region ID.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code to filter by (optional).
            region_id: UUID of region to filter by (optional).
            limit: Maximum number of cities to return (default 500).
            
        Returns:
            List of dictionaries with keys: id, country_code, region_id, name, normalized_name, created_at, updated_at
        """
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
