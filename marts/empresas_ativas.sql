-- Distribuição de empresas e estabelecimentos ativos do CNPJ por UF e porte
SELECT
    coalesce(est.uf, 'ND') AS uf,
    coalesce(emp.porte_empresa, '00') AS porte,
    count(*)::BIGINT AS total_estabelecimentos,
    count(CASE WHEN est.situacao_cadastral = '02' THEN 1 END)::BIGINT AS estabelecimentos_ativos,
    round(sum(coalesce(try_cast(emp.capital_social AS DOUBLE), 0.0)), 2) AS capital_social_total
FROM rfb_cnpj.estabelecimentos est
LEFT JOIN rfb_cnpj.empresas emp ON est.cnpj_basico = emp.cnpj_basico
GROUP BY 1, 2
ORDER BY uf, porte;
