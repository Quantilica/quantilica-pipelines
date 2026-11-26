SELECT municipio AS entidade,
       CAST(mes AS DATE) AS periodo,
       tipo AS d_tipo_registro,
       prelim AS a_preliminar_na_fonte,
       CAST(sinistros AS BIGINT) AS m_sinistros,
       CAST(media_vitimas AS DOUBLE) AS m_vitimas_por_sinistro
FROM base
WHERE regexp_matches(municipio, '^\d{7}$')
