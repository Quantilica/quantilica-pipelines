-- analytics.desembolsos_bndes
WITH joined_tables AS (
    SELECT
        sd.date,
        sd.series_id,
        sd.value,
        sm.name
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (7415, 7416, 7417, 7418, 7419)
        AND sd.ativo = TRUE
),
series_diffs AS (
    SELECT
        series_id,
        date,
        value::bigint - (lag(value::bigint) OVER (PARTITION BY series_id ORDER BY date)) AS value
    FROM
        joined_tables
),
series_january AS (
    SELECT
        series_id,
        date,
        value::bigint AS value
    FROM
        joined_tables
    WHERE EXTRACT('MONTH' FROM date) = 1
),
series_bndes AS (
    SELECT
        series_id,
        date,
        value
    FROM
        series_diffs
    WHERE EXTRACT('MONTH' FROM date) != 1
    UNION ALL
    SELECT
        series_id,
        date,
        value
    FROM
        series_january
),
series_correct_unit AS (
    SELECT
        date,
        series_id,
        (value * 1000000)::bigint AS value
    FROM
        series_bndes
),
bndes_metadata_processed AS (
    SELECT
        series_id,
        REPLACE(name, 'Desembolsos do sistema BNDES - ', '') AS setor
    FROM
        joined_tables
    GROUP BY
        series_id, name
)
SELECT
    t0.date,
    t1.setor,
    'R$' AS unidade,
    t0.value AS valor
FROM
    series_correct_unit AS t0
    LEFT JOIN bndes_metadata_processed AS t1 ON t0.series_id = t1.series_id
ORDER BY
    t0.date, t1.setor;
