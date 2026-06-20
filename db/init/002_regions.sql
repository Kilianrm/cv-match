-- Shared region catalog for all services.
-- This script is idempotent and can be re-run safely.

CREATE TABLE IF NOT EXISTS regions (
    id UUID PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL REFERENCES countries(code),
    name VARCHAR NOT NULL,
    normalized_name VARCHAR NOT NULL,
    code VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (country_code, normalized_name)
);

DO $$
BEGIN
    IF to_regclass('public.cities') IS NOT NULL THEN
        DELETE FROM cities
        WHERE country_code NOT IN (
            'AL','AD','AT','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IE',
            'IT','LV','LI','LT','LU','MT','MD','MC','ME','NL','MK','NO','PL','PT','RO','RU','SM','RS','SK',
            'SI','ES','SE','CH','UA','GB','VA'
        );
    END IF;

    DELETE FROM regions
    WHERE country_code NOT IN (
        'AL','AD','AT','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IE',
        'IT','LV','LI','LT','LU','MT','MD','MC','ME','NL','MK','NO','PL','PT','RO','RU','SM','RS','SK',
        'SI','ES','SE','CH','UA','GB','VA'
    );
END $$;

INSERT INTO regions (id, country_code, name, normalized_name, code)
VALUES
    ('00000001-0000-0000-0000-000000000001', 'AL', 'Tirana', 'tirana', 'TR'),
    ('00000002-0000-0000-0000-000000000002', 'AD', 'Andorra la Vella', 'andorra la vella', 'AD'),
    ('00000003-0000-0000-0000-000000000003', 'AT', 'Vienna', 'vienna', 'W'),
    ('00000004-0000-0000-0000-000000000004', 'BY', 'Minsk', 'minsk', 'HM'),
    ('00000005-0000-0000-0000-000000000005', 'BE', 'Brussels', 'brussels', 'BRU'),
    ('00000006-0000-0000-0000-000000000006', 'BA', 'Sarajevo', 'sarajevo', 'BR'),
    ('00000007-0000-0000-0000-000000000007', 'BG', 'Sofia', 'sofia', 'SO'),
    ('00000008-0000-0000-0000-000000000008', 'HR', 'Zagreb', 'zagreb', 'ZG'),
    ('00000009-0000-0000-0000-000000000009', 'CY', 'Nicosia', 'nicosia', 'NIC'),
    ('00000010-0000-0000-0000-000000000010', 'CZ', 'Prague', 'prague', 'PR'),
    ('00000011-0000-0000-0000-000000000011', 'DK', 'Copenhagen', 'copenhagen', 'KH'),
    ('00000012-0000-0000-0000-000000000012', 'EE', 'Tallinn', 'tallinn', 'TL'),
    ('00000013-0000-0000-0000-000000000013', 'FI', 'Helsinki', 'helsinki', 'HE'),
    ('00000014-0000-0000-0000-000000000014', 'FR', 'Ile-de-France', 'ile-de-france', 'IDF'),
    ('00000015-0000-0000-0000-000000000015', 'DE', 'Berlin', 'berlin', 'BE'),
    ('00000016-0000-0000-0000-000000000016', 'GR', 'Athens', 'athens', 'A'),
    ('00000017-0000-0000-0000-000000000017', 'HU', 'Budapest', 'budapest', 'BP'),
    ('00000018-0000-0000-0000-000000000018', 'IS', 'Reykjavik', 'reykjavik', 'RK'),
    ('00000019-0000-0000-0000-000000000019', 'IE', 'Dublin', 'dublin', 'D'),
    ('00000020-0000-0000-0000-000000000020', 'IT', 'Lazio', 'lazio', '62'),
    ('00000021-0000-0000-0000-000000000021', 'LV', 'Riga', 'riga', 'RI'),
    ('00000022-0000-0000-0000-000000000022', 'LI', 'Vaduz', 'vaduz', 'VA'),
    ('00000023-0000-0000-0000-000000000023', 'LT', 'Vilnius', 'vilnius', 'VL'),
    ('00000024-0000-0000-0000-000000000024', 'LU', 'Luxembourg City', 'luxembourg city', 'LC'),
    ('00000025-0000-0000-0000-000000000025', 'MT', 'Valletta', 'valletta', 'VL'),
    ('00000026-0000-0000-0000-000000000026', 'MD', 'Chisinau', 'chisinau', 'CH'),
    ('00000027-0000-0000-0000-000000000027', 'MC', 'Monaco', 'monaco', 'MC'),
    ('00000028-0000-0000-0000-000000000028', 'ME', 'Podgorica', 'podgorica', 'PD'),
    ('00000029-0000-0000-0000-000000000029', 'NL', 'North Holland', 'north holland', 'NH'),
    ('00000030-0000-0000-0000-000000000030', 'MK', 'Skopje', 'skopje', 'SK'),
    ('00000031-0000-0000-0000-000000000031', 'NO', 'Oslo', 'oslo', 'OS'),
    ('00000032-0000-0000-0000-000000000032', 'PL', 'Warsaw', 'warsaw', 'WA'),
    ('00000033-0000-0000-0000-000000000033', 'PT', 'Lisbon', 'lisbon', 'LI'),
    ('00000034-0000-0000-0000-000000000034', 'RO', 'Bucharest', 'bucharest', 'B'),
    ('00000035-0000-0000-0000-000000000035', 'RU', 'Moscow', 'moscow', 'MO'),
    ('00000036-0000-0000-0000-000000000036', 'SM', 'San Marino', 'san marino', 'SM'),
    ('00000037-0000-0000-0000-000000000037', 'RS', 'Belgrade', 'belgrade', 'BE'),
    ('00000038-0000-0000-0000-000000000038', 'SK', 'Bratislava', 'bratislava', 'BR'),
    ('00000039-0000-0000-0000-000000000039', 'SI', 'Ljubljana', 'ljubljana', 'LJ'),
    ('00000040-0000-0000-0000-000000000040', 'ES', 'Madrid', 'madrid', 'MD'),
    ('00000041-0000-0000-0000-000000000041', 'SE', 'Stockholm', 'stockholm', 'ST'),
    ('00000042-0000-0000-0000-000000000042', 'CH', 'Bern', 'bern', 'BE'),
    ('00000043-0000-0000-0000-000000000043', 'UA', 'Kyiv', 'kyiv', 'KY'),
    ('00000044-0000-0000-0000-000000000044', 'GB', 'England', 'england', 'ENG'),
    ('00000045-0000-0000-0000-000000000045', 'VA', 'Vatican City', 'vatican city', 'VA')
ON CONFLICT (id) DO UPDATE
SET
    country_code = EXCLUDED.country_code,
    name = EXCLUDED.name,
    normalized_name = EXCLUDED.normalized_name,
    code = EXCLUDED.code,
    updated_at = NOW();
