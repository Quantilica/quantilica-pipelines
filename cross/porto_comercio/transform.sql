-- cross.mart_porto_comercio
-- Cruzamento entre cargas portuárias (ANTAQ) e comércio exterior (Comex).
-- Nota: A associação instalação portuária <-> URF/município é aproximada
-- e baseada na correspondência de SH4 e territorialidade; a coluna confianca_join
-- explicita o nível de agregação correspondido.

WITH cargas AS (
    SELECT
        TRY_CAST(ano AS INTEGER) AS ano,
        LPAD(TRIM(mes), 2, '0') AS mes,
        TRIM(codigo_instalacao_portuaria) AS codigo_instalacao_portuaria,
        LPAD(TRIM(sh4), 4, '0') AS sh4,
        SUM(TRY_CAST(peso_liquido_kg AS DECIMAL(20, 2))) AS peso_porto_kg
    FROM antaq.cargas
    WHERE sh4 IS NOT NULL AND codigo_instalacao_portuaria IS NOT NULL
    GROUP BY 1, 2, 3, 4
),
comex AS (
    SELECT
        TRY_CAST(ano AS INTEGER) AS ano,
        LPAD(TRIM(mes), 2, '0') AS mes,
        SUBSTR(LPAD(TRIM(co_ncm), 8, '0'), 1, 4) AS sh4,
        SUM(TRY_CAST(kg_liquido AS DECIMAL(20, 2))) AS peso_comex_kg,
        SUM(TRY_CAST(vl_fob AS DECIMAL(20, 2))) AS valor_fob_usd
    FROM comex.trade_exp_ncm
    GROUP BY 1, 2, 3
)
SELECT
    c.ano,
    c.mes,
    c.codigo_instalacao_portuaria,
    c.sh4,
    c.peso_porto_kg,
    x.peso_comex_kg,
    x.valor_fob_usd,
    CASE WHEN x.sh4 IS NOT NULL THEN 'sh4_mes' ELSE 'sem_comex' END AS confianca_join
FROM cargas c
LEFT JOIN comex x ON c.ano = x.ano AND c.mes = x.mes AND c.sh4 = x.sh4
ORDER BY c.ano, c.mes, c.codigo_instalacao_portuaria, c.sh4;
