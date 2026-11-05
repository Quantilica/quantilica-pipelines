-- marts.fato_short_interest_b3
-- Junta a posição de aluguel (BTC) às cotações do COTAHIST no mesmo dia. O BTC é o
-- lado dominante (LEFT JOIN): ticker sem cotação no dia entra com métricas nulas,
-- para que a cobertura do join seja mensurável. Taxa e volume vêm da fonte.
--
-- Origem: b3.cotahist (alias do COTAHIST; colunas quantidade_titulos_negociados e
-- volume_negociado conforme auxiliary_tables/registro01.csv do b3-fetcher) e
-- b3.btc_posicoes_abertas. ATENÇÃO: o b3-fetcher ainda não coleta o BTC (sem URL no
-- catálogo), e as colunas do lado BTC não estão confirmadas contra dados reais; por
-- isso o pipeline está comentado no manifest.toml (ver "Dependência upstream").

WITH btc AS (
    SELECT
        b3_date(data_referencia)               AS data,
        UPPER(TRIM(simbolo))                   AS simbolo,
        MAX(NULLIF(TRIM(codigo_isin), ''))     AS codigo_isin,
        SUM(TRY_CAST(quantidade AS BIGINT))::BIGINT AS quantidade_alugada,
        SUM(TRY_CAST(valor AS DECIMAL(20, 2)))  AS valor_alugado,
        AVG(TRY_CAST(taxa_media AS DECIMAL(10, 4))) AS taxa_media
    FROM b3.btc_posicoes_abertas
    WHERE TRY_CAST(quantidade AS BIGINT) IS NOT NULL
    GROUP BY 1, 2
),
cot AS (
    SELECT
        b3_date(data)                                               AS data,
        UPPER(TRIM(simbolo))                                        AS simbolo,
        SUM(TRY_CAST(quantidade_titulos_negociados AS BIGINT))::BIGINT AS quantidade_negociada,
        SUM(TRY_CAST(volume_negociado AS DECIMAL(20, 2)))           AS volume
    FROM b3.cotahist
    WHERE b3_date(data) IS NOT NULL
    GROUP BY 1, 2
)
SELECT
    b.data,
    b.simbolo,
    b.codigo_isin,
    b.quantidade_alugada,
    b.valor_alugado,
    b.taxa_media,
    c.quantidade_negociada,
    c.volume,
    CASE WHEN c.quantidade_negociada > 0
         THEN ROUND(b.quantidade_alugada::DOUBLE / c.quantidade_negociada, 6)
    END AS razao_short_interest
FROM btc b
LEFT JOIN cot c USING (data, simbolo)
ORDER BY b.data, b.simbolo;
