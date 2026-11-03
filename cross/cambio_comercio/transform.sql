-- cross.mart_cambio_comercio
-- Confronto mensal entre fluxo cambial contratado (BCB) e saldo comercial (Comex).
--
-- ATENÇÃO: pipeline comentado no manifest.toml. A view bcb_microdados.fluxo_cambial_diario
-- não existe (aliases do conversor: scr, estban_municipio, estban_agencia, cosif).

WITH fluxo AS (
    SELECT
        TRY_CAST(ano AS INTEGER) AS ano,
        LPAD(TRIM(mes), 2, '0') AS mes,
        TRIM(natureza) AS natureza,
        SUM(TRY_CAST(valor_usd AS DECIMAL(20, 2))) AS fluxo_cambial_usd
    FROM bcb_microdados.fluxo_cambial_diario
    GROUP BY 1, 2, 3
),
comex_exp AS (
    SELECT
        TRY_CAST(ano AS INTEGER) AS ano,
        LPAD(TRIM(mes), 2, '0') AS mes,
        SUM(TRY_CAST(vl_fob AS DECIMAL(20, 2))) AS exportacoes_usd
    FROM comex.trade_exp_ncm
    GROUP BY 1, 2
),
comex_imp AS (
    SELECT
        TRY_CAST(ano AS INTEGER) AS ano,
        LPAD(TRIM(mes), 2, '0') AS mes,
        SUM(TRY_CAST(vl_fob AS DECIMAL(20, 2))) AS importacoes_usd
    FROM comex.trade_imp_ncm
    GROUP BY 1, 2
),
saldo AS (
    SELECT
        COALESCE(e.ano, i.ano) AS ano,
        COALESCE(e.mes, i.mes) AS mes,
        COALESCE(e.exportacoes_usd, 0) AS exportacoes_usd,
        COALESCE(i.importacoes_usd, 0) AS importacoes_usd,
        COALESCE(e.exportacoes_usd, 0) - COALESCE(i.importacoes_usd, 0) AS saldo_comercial_usd
    FROM comex_exp e
    FULL OUTER JOIN comex_imp i ON e.ano = i.ano AND e.mes = i.mes
)
SELECT
    f.ano,
    f.mes,
    f.natureza,
    f.fluxo_cambial_usd,
    s.saldo_comercial_usd,
    CASE WHEN s.saldo_comercial_usd <> 0
         THEN ROUND(f.fluxo_cambial_usd::DOUBLE / s.saldo_comercial_usd, 4)
    END AS razao_cambio_por_comercio
FROM fluxo f
LEFT JOIN saldo s ON f.ano = s.ano AND f.mes = s.mes
ORDER BY f.ano, f.mes, f.natureza;
