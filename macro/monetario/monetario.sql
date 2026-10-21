-- analytics.monetario
-- Painel mensal de agregados monetários.
-- Uma coluna por série, indexado por data (mês de referência).
--
-- Séries:
--   27791 - Meios de pagamento - M1 (saldo em final de período) - Novo
--   27810 - Meios de pagamento amplos - M2 (saldo em final de período) - Novo
--   27813 - Meios de pagamento amplos - M3 (saldo em final de período) - Novo
--   27815 - Meios de pagamento amplos - M4 (saldo em final de periodo) - Novo

SELECT
    sd.date,
    MAX(CASE WHEN sd.series_id = 27791 THEN sd.value END) AS m1_mi,
    MAX(CASE WHEN sd.series_id = 27810 THEN sd.value END) AS m2_mi,
    MAX(CASE WHEN sd.series_id = 27813 THEN sd.value END) AS m3_mi,
    MAX(CASE WHEN sd.series_id = 27815 THEN sd.value END) AS m4_mi
FROM series_data sd
WHERE sd.series_id IN (27791, 27810, 27813, 27815)
  AND sd.ativo = TRUE
GROUP BY sd.date
ORDER BY sd.date;
