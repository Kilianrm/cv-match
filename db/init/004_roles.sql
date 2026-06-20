-- Shared preferred role catalog for all services.
-- This script is idempotent and can be re-run safely.

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY,
    role_name TEXT NOT NULL,
    normalized_role TEXT NOT NULL UNIQUE,
    category TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_aliases (
    id UUID PRIMARY KEY,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

WITH seed(id, role_name, normalized_role, category) AS (
    VALUES
        ('20000000-0000-0000-0000-000000000001', 'Software Engineer', 'software engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000002', 'Backend Engineer', 'backend engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000003', 'Frontend Engineer', 'frontend engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000004', 'Full Stack Engineer', 'full stack engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000005', 'DevOps Engineer', 'devops engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000006', 'Site Reliability Engineer', 'site reliability engineer', 'engineering'),
        ('20000000-0000-0000-0000-000000000007', 'Data Engineer', 'data engineer', 'data'),
        ('20000000-0000-0000-0000-000000000008', 'Data Analyst', 'data analyst', 'data'),
        ('20000000-0000-0000-0000-000000000009', 'Data Scientist', 'data scientist', 'data'),
        ('20000000-0000-0000-0000-000000000010', 'Machine Learning Engineer', 'machine learning engineer', 'data'),
        ('20000000-0000-0000-0000-000000000011', 'Cloud Engineer', 'cloud engineer', 'infrastructure'),
        ('20000000-0000-0000-0000-000000000012', 'Cybersecurity Engineer', 'cybersecurity engineer', 'security'),
        ('20000000-0000-0000-0000-000000000013', 'QA Engineer', 'qa engineer', 'quality'),
        ('20000000-0000-0000-0000-000000000014', 'Product Manager', 'product manager', 'product'),
        ('20000000-0000-0000-0000-000000000015', 'Technical Project Manager', 'technical project manager', 'product'),
        ('20000000-0000-0000-0000-000000000016', 'UX Designer', 'ux designer', 'design'),
        ('20000000-0000-0000-0000-000000000017', 'UI Designer', 'ui designer', 'design'),
        ('20000000-0000-0000-0000-000000000018', 'Solutions Architect', 'solutions architect', 'architecture')
)
INSERT INTO roles (id, role_name, normalized_role, category)
SELECT id::uuid, role_name, normalized_role, category
FROM seed
ON CONFLICT (id) DO UPDATE
SET
    role_name = EXCLUDED.role_name,
    normalized_role = EXCLUDED.normalized_role,
    category = EXCLUDED.category,
    updated_at = NOW();

WITH alias_seed(id, role_id, alias, normalized_alias) AS (
    VALUES
        ('20000001-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Software Developer', 'software developer'),
        ('20000001-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'Application Developer', 'application developer'),
        ('20000001-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000002', 'Back End Engineer', 'back end engineer'),
        ('20000001-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000003', 'Front End Engineer', 'front end engineer'),
        ('20000001-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000004', 'Fullstack Engineer', 'fullstack engineer'),
        ('20000001-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000005', 'Platform Engineer', 'platform engineer'),
        ('20000001-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000009', 'ML Scientist', 'ml scientist'),
        ('20000001-0000-0000-0000-000000000008', '20000000-0000-0000-0000-000000000010', 'ML Engineer', 'ml engineer'),
        ('20000001-0000-0000-0000-000000000009', '20000000-0000-0000-0000-000000000013', 'Quality Assurance Engineer', 'quality assurance engineer'),
        ('20000001-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000014', 'PM', 'pm')
)
INSERT INTO role_aliases (id, role_id, alias, normalized_alias)
SELECT id::uuid, role_id::uuid, alias, normalized_alias
FROM alias_seed
ON CONFLICT (id) DO UPDATE
SET
    role_id = EXCLUDED.role_id,
    alias = EXCLUDED.alias,
    normalized_alias = EXCLUDED.normalized_alias;
