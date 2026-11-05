-- Movimentação formal de emprego por competência, UF e seção CNAE (Novo CAGED, movimentações).
-- Colunas do lake (pdet_fetcher NOVO_CAGED_HEADER_NAMES): id_uf é o código IBGE da UF,
-- cnae_2_secao a letra da seção, saldo_movimento e salario_mensal os valores.
SELECT
    printf('%04d-%02d', ano::INTEGER, mes::INTEGER) AS competencia,
    coalesce(id_uf, 'ND') AS uf,
    coalesce(cnae_2_secao, 'ND') AS grande_setor,
    sum(CASE WHEN tipo_movimentacao IN ('10', '20', '25', 'admissao') THEN 1 ELSE 0 END)::BIGINT AS admissoes,
    sum(CASE WHEN tipo_movimentacao IN ('31', '32', '40', 'desligamento') THEN 1 ELSE 0 END)::BIGINT AS desligamentos,
    sum(coalesce(try_cast(saldo_movimento AS INTEGER), 0))::BIGINT AS saldo_movimentacao,
    round(avg(coalesce(try_cast(CASE WHEN contains(salario_mensal::VARCHAR, ',') THEN replace(replace(salario_mensal::VARCHAR, '.', ''), ',', '.') ELSE salario_mensal::VARCHAR END AS DOUBLE), 0.0)), 2) AS salario_medio
FROM pdet.caged_2020_mov
GROUP BY 1, 2, 3
ORDER BY competencia DESC, uf, grande_setor;
