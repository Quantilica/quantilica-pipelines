SELECT
    sd.date,
    COALESCE(sd.date_end, sd.date) AS date_end,
    CASE sd.series_id
        WHEN 432 THEN 'SELIC-META'
        WHEN 11 THEN 'SELIC-OVER'
        WHEN 12 THEN 'CDI'
        WHEN 226 THEN 'TR'
        ELSE sm.name
    END AS taxa,
    sm.name AS nome_serie,
    sm.unit AS unidade,
    sm.frequency AS frequencia,
    sd.value::double precision AS valor
FROM
    series_data sd
    INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
WHERE
    sm.theme_hierarchy @> ARRAY['Mercados financeiros e de capitais', 'Indicadores do mercado financeiro', 'Taxas de juros']
    AND sd.ativo = TRUE
ORDER BY
    sd.date, date_end, taxa;
