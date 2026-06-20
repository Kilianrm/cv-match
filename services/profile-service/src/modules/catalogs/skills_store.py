"""Skills catalog data access layer."""

from typing import Optional

from psycopg import connect


class SkillsStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return connect(self.database_url)

    def get_skills(
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
                        SELECT id, skill_name, normalized_skill, category, created_at, updated_at
                        FROM skills
                        WHERE category = %s AND normalized_skill LIKE %s
                        ORDER BY skill_name ASC
                        LIMIT %s
                        """,
                        (category, f"%{' '.join(q.lower().split())}%", limit),
                    )
                elif q:
                    cur.execute(
                        """
                        SELECT id, skill_name, normalized_skill, category, created_at, updated_at
                        FROM skills
                        WHERE normalized_skill LIKE %s
                        ORDER BY skill_name ASC
                        LIMIT %s
                        """,
                        (f"%{' '.join(q.lower().split())}%", limit),
                    )
                elif category:
                    cur.execute(
                        """
                        SELECT id, skill_name, normalized_skill, category, created_at, updated_at
                        FROM skills
                        WHERE category = %s
                        ORDER BY skill_name ASC
                        LIMIT %s
                        """,
                        (category, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, skill_name, normalized_skill, category, created_at, updated_at
                        FROM skills
                        ORDER BY skill_name ASC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()
