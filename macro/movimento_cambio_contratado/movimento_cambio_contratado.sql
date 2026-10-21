-- analytics.movimento_cambio_contratado
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
    sm.theme_hierarchy @> ARRAY['Setor externo', 'Movimento de câmbio contratado']
    AND sd.ativo = TRUE
ORDER BY
    sd.date, sd.series_id;
