-- Novo CAGED por competência do evento, UF e município (códigos como na fonte).
-- Saldos de cada arquivo: `1` é admissão e `-1` é desligamento. As movimentações dentro do
-- prazo (mov) e fora do prazo (for) somam; as exclusões (exc) cancelam lançamentos já
-- declarados e entram com sinal trocado.
SELECT c, uf, m, sum(adm) AS adm, sum(des) AS des
FROM (
    SELECT competenciamov AS c, uf, municipio AS m,
           1 * count(*) FILTER (WHERE saldomovimentacao = '1') AS adm,
           1 * count(*) FILTER (WHERE saldomovimentacao = '-1') AS des
    FROM read_parquet($mov, union_by_name = true)
    GROUP BY 1, 2, 3
    UNION ALL
    SELECT competenciamov AS c, uf, municipio AS m,
           1 * count(*) FILTER (WHERE saldomovimentacao = '1') AS adm,
           1 * count(*) FILTER (WHERE saldomovimentacao = '-1') AS des
    FROM read_parquet($fora, union_by_name = true)
    GROUP BY 1, 2, 3
    UNION ALL
    SELECT competenciamov AS c, uf, municipio AS m,
           -1 * count(*) FILTER (WHERE saldomovimentacao = '1') AS adm,
           -1 * count(*) FILTER (WHERE saldomovimentacao = '-1') AS des
    FROM read_parquet($exclusoes, union_by_name = true)
    GROUP BY 1, 2, 3
)
GROUP BY 1, 2, 3
