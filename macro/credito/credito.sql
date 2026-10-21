-- analytics.credito
-- Painel mensal de operações de crédito do sistema financeiro.
-- Uma coluna por série, indexado por data (mês de referência).
--
-- Séries:
--   20539 Crédito total - saldo (R$ milhões)
--   21082 Inadimplência total - % da carteira de crédito
--   20783 Spread médio total das operações de crédito (p.p.)

SELECT
    sd.date,
    MAX(CASE WHEN sd.series_id = 20539 THEN sd.value END) AS credito_saldo_mi,
    MAX(CASE WHEN sd.series_id = 21082 THEN sd.value END) AS inadimplencia_pct,
    MAX(CASE WHEN sd.series_id = 20783 THEN sd.value END) AS spread_pp
FROM series_data sd
WHERE sd.series_id IN (20539, 21082, 20783)
  AND sd.ativo = TRUE
GROUP BY sd.date
ORDER BY sd.date;
