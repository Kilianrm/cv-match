-- Shared degree type catalog for all services.
-- This script is idempotent and can be re-run safely.

CREATE TABLE IF NOT EXISTS degree_types (
    id UUID PRIMARY KEY,
    degree_name TEXT NOT NULL,
    normalized_degree TEXT NOT NULL UNIQUE,
    level SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

WITH seed(id, degree_name, normalized_degree, level) AS (
    VALUES
        ('30000000-0000-0000-0000-000000000001', 'High School Diploma', 'high school diploma', 1),
        ('30000000-0000-0000-0000-000000000002', 'Associate Degree', 'associate degree', 2),
        ('30000000-0000-0000-0000-000000000003', 'Bachelor Degree', 'bachelor degree', 3),
        ('30000000-0000-0000-0000-000000000004', 'Postgraduate Diploma', 'postgraduate diploma', 4),
        ('30000000-0000-0000-0000-000000000005', 'Master Degree', 'master degree', 5),
        ('30000000-0000-0000-0000-000000000006', 'Doctorate (PhD)', 'doctorate phd', 6),
        ('30000000-0000-0000-0000-000000000007', 'Bootcamp Certificate', 'bootcamp certificate', 2),
        ('30000000-0000-0000-0000-000000000008', 'Professional Certificate', 'professional certificate', 2)
)
INSERT INTO degree_types (id, degree_name, normalized_degree, level)
SELECT id::uuid, degree_name, normalized_degree, level
FROM seed
ON CONFLICT (id) DO UPDATE
SET
    degree_name = EXCLUDED.degree_name,
    normalized_degree = EXCLUDED.normalized_degree,
    level = EXCLUDED.level,
    updated_at = NOW();
