-- analytics.energia_eletrica
WITH joined_tables AS (
    SELECT
        sd.date,
        sd.series_id,
        sd.value,
        sm.unit
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (1402, 1403, 1404, 1405, 1406)
        AND sd.ativo = TRUE
),
energia_eletrica_metadata_processed AS (
    SELECT
        series_id,
        (
            CASE series_id
                WHEN 1402 THEN 'Comercial'
                WHEN 1403 THEN 'Residencial'
                WHEN 1404 THEN 'Industrial'
                WHEN 1405 THEN 'Outros'
                WHEN 1406 THEN 'Total'
            END
        ) AS setor,
        unit AS unidade
    FROM
        joined_tables
    GROUP BY
        series_id, unit
)
SELECT
    t0.date,
    t1.setor,
    t1.unidade,
    t0.value AS valor
FROM
    joined_tables AS t0
    LEFT JOIN energia_eletrica_metadata_processed AS t1
        ON t0.series_id = t1.series_id
ORDER BY
    t0.date, t1.setor;
