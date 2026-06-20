-- Shared country catalog for all services.
-- This script is idempotent and can be re-run safely.

CREATE TABLE IF NOT EXISTS countries (
    code VARCHAR(2) PRIMARY KEY,
    name VARCHAR NOT NULL,
    normalized_name VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

    IF to_regclass('public.regions') IS NOT NULL THEN
        DELETE FROM regions
        WHERE country_code NOT IN (
            'AL','AD','AT','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IE',
            'IT','LV','LI','LT','LU','MT','MD','MC','ME','NL','MK','NO','PL','PT','RO','RU','SM','RS','SK',
            'SI','ES','SE','CH','UA','GB','VA'
        );
    END IF;

    DELETE FROM countries
    WHERE code NOT IN (
        'AL','AD','AT','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IE',
        'IT','LV','LI','LT','LU','MT','MD','MC','ME','NL','MK','NO','PL','PT','RO','RU','SM','RS','SK',
        'SI','ES','SE','CH','UA','GB','VA'
    );
END $$;

INSERT INTO countries (code, name, normalized_name)
VALUES
    ('AL', 'Albania', 'albania'),
    ('AD', 'Andorra', 'andorra'),
    ('AT', 'Austria', 'austria'),
    ('BY', 'Belarus', 'belarus'),
    ('BE', 'Belgium', 'belgium'),
    ('BA', 'Bosnia and Herzegovina', 'bosnia and herzegovina'),
    ('BG', 'Bulgaria', 'bulgaria'),
    ('HR', 'Croatia', 'croatia'),
    ('CY', 'Cyprus', 'cyprus'),
    ('CZ', 'Czechia', 'czechia'),
    ('DK', 'Denmark', 'denmark'),
    ('EE', 'Estonia', 'estonia'),
    ('FI', 'Finland', 'finland'),
    ('FR', 'France', 'france'),
    ('DE', 'Germany', 'germany'),
    ('GR', 'Greece', 'greece'),
    ('HU', 'Hungary', 'hungary'),
    ('IS', 'Iceland', 'iceland'),
    ('IE', 'Ireland', 'ireland'),
    ('IT', 'Italy', 'italy'),
    ('LV', 'Latvia', 'latvia'),
    ('LI', 'Liechtenstein', 'liechtenstein'),
    ('LT', 'Lithuania', 'lithuania'),
    ('LU', 'Luxembourg', 'luxembourg'),
    ('MT', 'Malta', 'malta'),
    ('MD', 'Moldova', 'moldova'),
    ('MC', 'Monaco', 'monaco'),
    ('ME', 'Montenegro', 'montenegro'),
    ('NL', 'Netherlands', 'netherlands'),
    ('MK', 'North Macedonia', 'north macedonia'),
    ('NO', 'Norway', 'norway'),
    ('PL', 'Poland', 'poland'),
    ('PT', 'Portugal', 'portugal'),
    ('RO', 'Romania', 'romania'),
    ('RU', 'Russia', 'russia'),
    ('SM', 'San Marino', 'san marino'),
    ('RS', 'Serbia', 'serbia'),
    ('SK', 'Slovakia', 'slovakia'),
    ('SI', 'Slovenia', 'slovenia'),
    ('ES', 'Spain', 'spain'),
    ('SE', 'Sweden', 'sweden'),
    ('CH', 'Switzerland', 'switzerland'),
    ('UA', 'Ukraine', 'ukraine'),
    ('GB', 'United Kingdom', 'united kingdom'),
    ('VA', 'Vatican City', 'vatican city')
ON CONFLICT (code) DO UPDATE
SET
    name = EXCLUDED.name,
    normalized_name = EXCLUDED.normalized_name,
    updated_at = NOW();
