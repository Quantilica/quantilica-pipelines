-- analytics.pib_mensal
WITH raw_pib_mensal AS (
    SELECT
        date,
        series_id,
        value
    FROM
        series_data
    WHERE
        series_id IN (4380, 4385)
        AND ativo = TRUE
),
pib_mensal_corrected_unit AS (
    SELECT
        date,
        series_id,
        (value * 1000000)::bigint AS value
    FROM
        raw_pib_mensal
),
fin AS (
    SELECT
        date,
        SUM(
            CASE series_id
                WHEN 4380 THEN value ELSE NULL
            END
        ) AS pib_brl,
        SUM(
            CASE series_id
                WHEN 4385 THEN value ELSE NULL
            END
        ) AS pib_usd
    FROM
        pib_mensal_corrected_unit
    GROUP BY
        date
)
SELECT
    date,
    pib_brl,
    pib_usd
FROM
    fin
ORDER BY
    date;
