-- Movimentação formal de emprego por competência e UF (CAGED Movimentações)
SELECT
    printf('%04d-%02d', ano, mes) AS competencia,
    coalesce(uf, 'ND') AS uf,
    coalesce(secao, 'ND') AS grande_setor,
    sum(CASE WHEN tipomovimentacao IN ('10', '20', '25', 'admissao') THEN 1 ELSE 0 END)::BIGINT AS admissoes,
    sum(CASE WHEN tipomovimentacao IN ('31', '32', '40', 'desligamento') THEN 1 ELSE 0 END)::BIGINT AS desligamentos,
    sum(coalesce(try_cast(saldomovimentacao AS INTEGER), 0))::BIGINT AS saldo_movimentacao,
    round(avg(coalesce(try_cast(replace(replace(salario, '.', ''), ',', '.') AS DOUBLE), 0.0)), 2) AS salario_medio
FROM pdet.caged_2020_mov
GROUP BY 1, 2, 3
ORDER BY competencia DESC, uf;
