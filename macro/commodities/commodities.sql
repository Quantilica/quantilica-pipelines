-- analytics.commodities
WITH raw_commodities AS (
    SELECT
        sd.date,
        sd.series_id,
        sm.name AS nome_serie,
        sm.unit AS unidade,
        sm.frequency AS frequencia,
        sd.value::double precision AS valor
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (27574, 27575, 27577, 27576)
        AND sd.ativo = TRUE
)
SELECT
    date,
    CASE series_id
        WHEN 27574 THEN 'Total'
        WHEN 27575 THEN 'Agropecuária'
        WHEN 27576 THEN 'Metal'
        WHEN 27577 THEN 'Energia'
        ELSE nome_serie
    END AS commodity,
    nome_serie,
    unidade,
    frequencia,
    valor
FROM
    raw_commodities
ORDER BY
    date, commodity;
