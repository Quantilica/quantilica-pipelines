-- Pipeline Cross-Domain: Macroeconômico + Mercado de Trabalho
-- Integração da camada analytics entre múltiplas fontes:
-- - Inflação: IPCA taxa mensal de analytics.precos
-- - Juros: SELIC-OVER taxa diária agregada mensal de analytics.juros
-- - Emprego: Taxa de desocupação oficial (PNAD Contínua tabela 6785 Brasil) de analytics.pnadcm_ocupada

DROP VIEW IF EXISTS analytics.macro_trabalho_indicadores;

CREATE OR REPLACE VIEW analytics.macro_trabalho_indicadores AS
WITH ipca_mensal AS (
    SELECT
        date_trunc('month', date)::date AS data_mes,
        valor AS ipca_taxa_mensal
    FROM analytics.precos
    WHERE indice = 'IPCA'
),
selic_mensal AS (
    SELECT
        date_trunc('month', date)::date AS data_mes,
        round(avg(valor)::numeric, 4) AS selic_media_mensal
    FROM analytics.juros
    WHERE taxa = 'SELIC-OVER'
    GROUP BY date_trunc('month', date)::date
),
desocupacao_mensal AS (
    SELECT
        date_trunc('month', periodo)::date AS data_mes,
        valor AS taxa_desocupacao_pnad
    FROM analytics.pnadcm_ocupada
    WHERE tabela_sidra_id = '6785'
      AND localidade_id = '1'
      AND classificacao_id IS NULL
)
SELECT
    COALESCE(i.data_mes, s.data_mes, d.data_mes) AS date,
    i.ipca_taxa_mensal,
    s.selic_media_mensal,
    d.taxa_desocupacao_pnad
FROM ipca_mensal i
FULL OUTER JOIN selic_mensal s ON i.data_mes = s.data_mes
FULL OUTER JOIN desocupacao_mensal d ON COALESCE(i.data_mes, s.data_mes) = d.data_mes
ORDER BY date DESC;
