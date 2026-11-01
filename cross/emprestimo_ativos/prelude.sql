-- Preparação compartilhada para o mart de short interest (DuckDB sobre o lake).
SET TimeZone = 'UTC';

CREATE OR REPLACE MACRO b3_date(x) AS
    COALESCE(
        TRY_STRPTIME(TRIM(x), '%Y-%m-%d'),
        TRY_STRPTIME(TRIM(x), '%d/%m/%Y'),
        TRY_STRPTIME(TRIM(x), '%Y%m%d')
    )::DATE;

CREATE OR REPLACE MACRO b3_decimal(x) AS
    CASE
        WHEN regexp_matches(replace(replace(TRIM(x), '.', ''), ',', '.'), '^-?[0-9]+(\.[0-9]+)?$')
        THEN CAST(replace(replace(TRIM(x), '.', ''), ',', '.') AS DECIMAL(20, 2))
    END;
