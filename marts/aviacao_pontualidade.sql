-- Indicadores de pontualidade e tráfego de voos por aeródromo (ANAC Voo Regular Ativo)
SELECT
    coalesce(icao_aerodromo_origem, 'ND') AS aerodromo,
    ano::INTEGER AS ano,
    mes::INTEGER AS mes,
    count(*)::BIGINT AS total_voos_programados,
    count(CASE WHEN situacao_voo = 'REALIZADO' THEN 1 END)::BIGINT AS voos_realizados,
    count(CASE WHEN situacao_voo = 'CANCELADO' THEN 1 END)::BIGINT AS voos_cancelados,
    round(100.0 * count(CASE WHEN situacao_voo = 'CANCELADO' THEN 1 END) / nullif(count(*), 0), 2) AS taxa_cancelamento_pct
FROM anac.vra
GROUP BY 1, 2, 3
ORDER BY ano DESC, mes DESC, aerodromo;
