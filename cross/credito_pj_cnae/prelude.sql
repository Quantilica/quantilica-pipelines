-- Preparação compartilhada para o mart de crédito PJ por CNAE.
SET TimeZone = 'UTC';

CREATE OR REPLACE MACRO scr_date(x) AS
    COALESCE(
        TRY_STRPTIME(TRIM(x), '%Y-%m-%d'),
        TRY_STRPTIME(TRIM(x), '%Y%m')
    )::DATE;
