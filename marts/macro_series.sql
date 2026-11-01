-- Séries macroeconômicas mensais unificadas de taxas de juros (Tesouro Direto Selic, IPCA+ e Prefixado)
SELECT
    date_trunc('month', coalesce(try_strptime(data_base, '%d/%m/%Y'), try_strptime(data_base, '%Y-%m-%d')))::DATE AS data,
    round(avg(CASE WHEN tipo_titulo ILIKE '%selic%' THEN try_cast(CASE WHEN contains(taxa_compra_manha::VARCHAR, ',') THEN replace(replace(taxa_compra_manha::VARCHAR, '.', ''), ',', '.') ELSE taxa_compra_manha::VARCHAR END AS DOUBLE) END), 4) AS taxa_selic_media,
    round(avg(CASE WHEN tipo_titulo ILIKE '%ipca+%' AND tipo_titulo NOT ILIKE '%semestrais%' THEN try_cast(CASE WHEN contains(taxa_compra_manha::VARCHAR, ',') THEN replace(replace(taxa_compra_manha::VARCHAR, '.', ''), ',', '.') ELSE taxa_compra_manha::VARCHAR END AS DOUBLE) END), 4) AS taxa_ipca_media,
    round(avg(CASE WHEN tipo_titulo ILIKE '%prefixado%' AND tipo_titulo NOT ILIKE '%semestrais%' THEN try_cast(CASE WHEN contains(taxa_compra_manha::VARCHAR, ',') THEN replace(replace(taxa_compra_manha::VARCHAR, '.', ''), ',', '.') ELSE taxa_compra_manha::VARCHAR END AS DOUBLE) END), 4) AS taxa_prefixado_media
FROM tesouro_direto.taxas
WHERE data_base IS NOT NULL
GROUP BY 1
HAVING data IS NOT NULL
ORDER BY data DESC;
