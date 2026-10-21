-- analytics.precos
SELECT
    sd.date,
    CASE sd.series_id
        WHEN 433 THEN 'IPCA'
        WHEN 13522 THEN 'IPCA-12M'
        WHEN 188 THEN 'INPC'
        WHEN 189 THEN 'IGP-M'
        WHEN 7478 THEN 'IPCA-15'
        ELSE sm.name
    END AS indice,
    sm.name AS nome_serie,
    sm.unit AS unidade,
    sm.frequency AS frequencia,
    sd.value::double precision AS valor
FROM
    series_data sd
    INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
WHERE
    sm.theme_hierarchy @> ARRAY['Atividade econômica e preços', 'Preços']
    AND sd.ativo = TRUE
ORDER BY
    sd.date, indice;
