SELECT uf AS entidade,
       CAST(mes AS DATE) AS periodo,
       tipo AS d_tipo_registro,
       bool_or(prelim) AS a_preliminar_na_fonte,
       CAST(sum(sinistros) AS BIGINT) AS m_sinistros,
       CAST(sum(media_vitimas * sinistros) / sum(sinistros) AS DOUBLE) AS m_vitimas_por_sinistro
FROM base
GROUP BY uf, mes, tipo
