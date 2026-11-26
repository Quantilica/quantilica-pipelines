-- Novo CAGED por município (código IBGE de 6 dígitos, como na fonte) e competência.
-- Município ignorado (999999) ou fora do padrão fica de fora (ver caged_mun_descartes.sql).
SELECT b.m AS entidade,
       make_date(CAST(substr(b.c, 1, 4) AS INTEGER), CAST(substr(b.c, 5, 2) AS INTEGER), 1) AS periodo,
       CAST(sum(b.adm) - sum(b.des) AS BIGINT) AS m_saldo,
       CAST(sum(b.adm) AS BIGINT) AS m_admissoes,
       CAST(sum(b.des) AS BIGINT) AS m_desligamentos
FROM base b
WHERE regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$')
  AND regexp_matches(b.m, '^\d{6}$') AND b.m <> '999999'
GROUP BY 1, 2
HAVING sum(b.adm) <> 0 OR sum(b.des) <> 0
ORDER BY 2, 1
