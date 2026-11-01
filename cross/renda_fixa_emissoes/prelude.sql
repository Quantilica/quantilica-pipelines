-- Preparação compartilhada para o mart de renda fixa e emissões.
SET TimeZone = 'UTC';

CREATE OR REPLACE MACRO cvm_date(x) AS
    COALESCE(
        TRY_STRPTIME(TRIM(x), '%Y-%m-%d'),
        TRY_STRPTIME(TRIM(x), '%d/%m/%Y'),
        TRY_STRPTIME(TRIM(x), '%Y%m%d')
    )::DATE;

CREATE OR REPLACE MACRO cvm_decimal(x) AS
    CASE
        WHEN regexp_matches(replace(replace(TRIM(x), '.', ''), ',', '.'), '^-?[0-9]+(\.[0-9]+)?$')
        THEN CAST(replace(replace(TRIM(x), '.', ''), ',', '.') AS DECIMAL(20, 2))
    END;

CREATE OR REPLACE MACRO clean_cnpj(x) AS
    LPAD(regexp_replace(TRIM(x), '[^0-9]', '', 'g'), 14, '0');
