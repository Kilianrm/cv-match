from __future__ import annotations

from uuid import UUID


class BaseProfileStoreMixin:
    def get_profile(self, user_id: str) -> dict | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        u.email,
                        p.full_name,
                        p.headline,
                        p.summary,
                        p.country_code,
                        p.region_id,
                        p.city_id,
                        p.years_experience,
                        p.work_mode_preference,
                        c.name AS country_name,
                        r.name AS region_name,
                        ci.name AS city_name,
                        p.location
                    FROM profiles p
                    JOIN users u ON u.id = p.user_id
                    LEFT JOIN countries c ON c.code = p.country_code
                    LEFT JOIN regions r ON r.id = p.region_id
                    LEFT JOIN cities ci ON ci.id = p.city_id
                    WHERE p.user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                (
                    email,
                    full_name,
                    headline,
                    summary,
                    country_code,
                    region_id,
                    city_id,
                    years_experience,
                    work_mode_preference,
                    country_name,
                    region_name,
                    city_name,
                    legacy_location,
                ) = row

                cur.execute(
                    """
                    SELECT s.id, s.skill_name, ps.proficiency_level
                    FROM profile_skills ps
                    JOIN skills s ON s.id = ps.skill_id
                    WHERE ps.profile_id = %s
                    ORDER BY ps.sort_order ASC, s.skill_name ASC
                    """,
                    (user_id,),
                )
                skills = [
                    {"skill_id": str(r[0]), "label": r[1], "proficiency_level": r[2]}
                    for r in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT id, role_id, role_name
                    FROM profile_preferred_roles
                    WHERE profile_id = %s
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    (user_id,),
                )
                preferred_roles = [
                    {
                        "id": str(r[0]),
                        "role_id": str(r[1]) if r[1] else None,
                        "role_name": r[2],
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT id, position, company, start_date, end_date, is_current, responsibilities
                    FROM profile_experience
                    WHERE profile_id = %s
                    ORDER BY sort_order ASC, start_date DESC
                    """,
                    (user_id,),
                )
                experience = []
                for r in cur.fetchall():
                    responsibilities = r[6] if isinstance(r[6], list) else []
                    experience.append(
                        {
                            "id": str(r[0]),
                            "position": r[1],
                            "company": r[2],
                            "start_date": r[3].isoformat() if r[3] else None,
                            "end_date": r[4].isoformat() if r[4] else None,
                            "is_current": r[5],
                            "responsibilities": responsibilities,
                        }
                    )

                cur.execute(
                    """
                    SELECT id, degree_type_id, degree, institution, start_date, end_date, status
                    FROM profile_education
                    WHERE profile_id = %s
                    ORDER BY sort_order ASC, start_date DESC NULLS LAST
                    """,
                    (user_id,),
                )
                education = [
                    {
                        "id": str(r[0]),
                        "degree_type_id": str(r[1]) if r[1] else None,
                        "degree": r[2],
                        "institution": r[3],
                        "start_date": r[4].isoformat() if r[4] else None,
                        "end_date": r[5].isoformat() if r[5] else None,
                        "status": r[6],
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT id, name, issuer, issued_at, expires_at
                    FROM profile_certifications
                    WHERE profile_id = %s
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                )
                certifications = [
                    {
                        "id": str(r[0]),
                        "name": r[1],
                        "issuer": r[2],
                        "issued_at": r[3].isoformat() if r[3] else None,
                        "expires_at": r[4].isoformat() if r[4] else None,
                    }
                    for r in cur.fetchall()
                ]

                location_obj = {
                    "country": {"code": country_code, "name": country_name} if country_code else None,
                    "region": {"id": str(region_id), "name": region_name} if region_id else None,
                    "city": {"id": str(city_id), "name": city_name} if city_id else None,
                }

                profile_obj = {
                    "full_name": full_name,
                    "headline": headline,
                    "summary": summary,
                    "country_code": country_code,
                    "region_id": str(region_id) if region_id else None,
                    "city_id": str(city_id) if city_id else None,
                    "years_experience": years_experience,
                    "work_mode_preference": work_mode_preference,
                    "legacy_location": legacy_location,
                }

                return {
                    "user": {
                        "user_id": user_id,
                        "email": email,
                    },
                    "profile": profile_obj,
                    "location": location_obj,
                    "skills": skills,
                    "preferred_roles": preferred_roles,
                    "experience": experience,
                    "education": education,
                    "certifications": certifications,
                    "cv": None,
                }

    def validate_base_profile_payload(self, data: dict) -> dict:
        normalized = dict(data)

        full_name = self._normalize_optional_text(normalized.get("full_name"))
        if not full_name:
            raise ValueError("full_name is required")
        normalized["full_name"] = full_name

        normalized["headline"] = self._normalize_optional_text(normalized.get("headline"))
        normalized["summary"] = self._normalize_optional_text(normalized.get("summary"))
        normalized["location"] = self._normalize_optional_text(normalized.get("location"))

        country_code = self._normalize_optional_text(normalized.get("country_code"))
        if country_code:
            country_code = country_code.upper()
            if len(country_code) != 2:
                raise ValueError("country_code must be an ISO alpha-2 code")
        normalized["country_code"] = country_code

        region_id = self._normalize_optional_text(normalized.get("region_id"))
        city_id = self._normalize_optional_text(normalized.get("city_id"))

        if region_id:
            try:
                region_id = str(UUID(region_id))
            except ValueError as exc:
                raise ValueError("region_id must be a valid UUID") from exc
        if city_id:
            try:
                city_id = str(UUID(city_id))
            except ValueError as exc:
                raise ValueError("city_id must be a valid UUID") from exc

        if city_id and not region_id:
            raise ValueError("region_id is required when city_id is provided")
        if region_id and not country_code:
            raise ValueError("country_code is required when region_id is provided")

        years_experience = normalized.get("years_experience")
        if years_experience is not None:
            if years_experience < 0 or years_experience > 60:
                raise ValueError("years_experience must be between 0 and 60")

        work_mode = self._normalize_optional_text(normalized.get("work_mode_preference"))
        if work_mode:
            work_mode = work_mode.lower()
            allowed_work_modes = {"remote", "hybrid", "onsite"}
            if work_mode not in allowed_work_modes:
                raise ValueError("work_mode_preference must be one of: remote, hybrid, onsite")
        normalized["work_mode_preference"] = work_mode

        normalized["region_id"] = region_id
        normalized["city_id"] = city_id

        with self._connect() as conn:
            with conn.cursor() as cur:
                if country_code:
                    cur.execute("SELECT 1 FROM countries WHERE code = %s", (country_code,))
                    if cur.fetchone() is None:
                        raise ValueError("country_code does not exist")

                if region_id:
                    cur.execute(
                        "SELECT country_code FROM regions WHERE id = %s",
                        (region_id,),
                    )
                    region_row = cur.fetchone()
                    if region_row is None:
                        raise ValueError("region_id does not exist")
                    if country_code and region_row[0] != country_code:
                        raise ValueError("region_id does not belong to country_code")

                if city_id:
                    cur.execute(
                        "SELECT country_code, region_id FROM cities WHERE id = %s",
                        (city_id,),
                    )
                    city_row = cur.fetchone()
                    if city_row is None:
                        raise ValueError("city_id does not exist")
                    if country_code and city_row[0] != country_code:
                        raise ValueError("city_id does not belong to country_code")
                    if region_id and str(city_row[1]) != region_id:
                        raise ValueError("city_id does not belong to region_id")

        return normalized

    def upsert_profile(self, user_id: str, data: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO profiles (
                        user_id,
                        full_name,
                        headline,
                        location,
                        summary,
                        country_code,
                        region_id,
                        city_id,
                        years_experience,
                        work_mode_preference
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                        SET full_name = EXCLUDED.full_name,
                            headline = EXCLUDED.headline,
                            location = EXCLUDED.location,
                            summary = EXCLUDED.summary,
                            country_code = EXCLUDED.country_code,
                            region_id = EXCLUDED.region_id,
                            city_id = EXCLUDED.city_id,
                            years_experience = EXCLUDED.years_experience,
                            work_mode_preference = EXCLUDED.work_mode_preference,
                            updated_at = NOW()
                    """,
                    (
                        user_id,
                        data.get("full_name"),
                        data.get("headline"),
                        data.get("location"),
                        data.get("summary"),
                        data.get("country_code"),
                        data.get("region_id"),
                        data.get("city_id"),
                        data.get("years_experience"),
                        data.get("work_mode_preference"),
                    ),
                )
