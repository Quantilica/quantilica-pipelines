-- O que o CAGED por município deixa de fora: competência inválida, município ignorado
-- (999999) ou fora do padrão. Entra em carga.detalhes como auditoria.
SELECT CASE WHEN regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$')
            THEN substr(b.c, 1, 4) || '-' || substr(b.c, 5, 2)
            ELSE 'invalida' END AS periodo,
       CAST(sum(b.adm) AS BIGINT) AS m_admissoes,
       CAST(sum(b.des) AS BIGINT) AS m_desligamentos
FROM base b
WHERE NOT coalesce(regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$'), false)
   OR NOT coalesce(regexp_matches(b.m, '^\d{6}$') AND b.m <> '999999', false)
GROUP BY 1
ORDER BY 1
