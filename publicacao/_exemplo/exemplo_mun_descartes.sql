SELECT 'sem_municipio' AS periodo, CAST(sum(sinistros) AS BIGINT) AS m_sinistros
FROM base
WHERE NOT regexp_matches(municipio, '^\d{7}$')
