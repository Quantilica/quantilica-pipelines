-- Exemplo: uma linha por (município, mês, tipo de registro).
SELECT municipio, uf, date_trunc('month', CAST(data AS DATE)) AS mes, tipo,
       count(*) AS sinistros, avg(CAST(vitimas AS DOUBLE)) AS media_vitimas, bool_or(CAST(preliminar AS BOOLEAN)) AS prelim
FROM read_parquet($sinistros, union_by_name = true)
GROUP BY 1, 2, 3, 4
