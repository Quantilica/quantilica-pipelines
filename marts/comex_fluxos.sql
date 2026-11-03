-- Fluxos consolidados de comércio exterior por ano, mês, UF e tipo de operação (COMEX Stat)
SELECT
    ano::INTEGER AS ano,
    co_mes::INTEGER AS mes,
    coalesce(sg_uf_ncm, 'ND') AS uf,
    'EXP' AS tipo_operacao,
    count(*)::BIGINT AS total_registros,
    round(sum(coalesce(vl_fob::DOUBLE, 0.0)), 2) AS valor_fob_usd,
    round(sum(coalesce(kg_liquido::DOUBLE, 0.0)), 2) AS peso_liquido_kg
FROM comex.trade_exp_ncm
GROUP BY 1, 2, 3
UNION ALL
SELECT
    ano::INTEGER AS ano,
    co_mes::INTEGER AS mes,
    coalesce(sg_uf_ncm, 'ND') AS uf,
    'IMP' AS tipo_operacao,
    count(*)::BIGINT AS total_registros,
    round(sum(coalesce(vl_fob::DOUBLE, 0.0)), 2) AS valor_fob_usd,
    round(sum(coalesce(kg_liquido::DOUBLE, 0.0)), 2) AS peso_liquido_kg
FROM comex.trade_imp_ncm
GROUP BY 1, 2, 3
ORDER BY ano DESC, mes DESC, uf;
