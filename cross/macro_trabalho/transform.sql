-- Pipeline Cross-Domain: Macroeconômico + Mercado de Trabalho
-- Integração da camada analytics entre múltiplas fontes

CREATE OR REPLACE VIEW analytics.macro_trabalho_indicadores AS
SELECT 
    coalesce(p.date, j.date) AS date,
    p.valor AS ipca_mensal,
    j.valor AS taxa_juros
FROM analytics.precos p
FULL OUTER JOIN analytics.juros j ON p.date = j.date
ORDER BY date DESC;
