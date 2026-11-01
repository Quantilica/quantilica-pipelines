-- cross.mart_renda_fixa_emissoes
-- Consolida ofertas de distribuição e certificados de securitização (CRI e CRA)
-- cruzando com carteiras de índices da B3 (IFIX, etc.).

WITH ofertas AS (
    SELECT
        CAST(SUBSTR(CAST(data_abertura_processo AS VARCHAR), 1, 7) || '-01' AS DATE) AS competencia,
        clean_cnpj(cnpj_emissor) AS cnpj_emissor,
        UPPER(TRIM(codigo_isin)) AS codigo_isin,
        'oferta' AS origem,
        nome_emissor,
        TRY_CAST(valor_total_oferta AS DECIMAL(20, 2)) AS valor_emissao
    FROM cvm.ofertas_distribuicao
    WHERE codigo_isin IS NOT NULL AND TRIM(codigo_isin) <> ''
),
cri AS (
    SELECT
        CAST(ano || '-01-01' AS DATE) AS competencia,
        clean_cnpj(cnpj_securitizadora) AS cnpj_emissor,
        UPPER(TRIM(codigo_isin)) AS codigo_isin,
        'cri' AS origem,
        nome_securitizadora AS nome_emissor,
        TRY_CAST(valor_emissao AS DECIMAL(20, 2)) AS valor_emissao
    FROM cvm.securitizacao_cri
    WHERE codigo_isin IS NOT NULL AND TRIM(codigo_isin) <> ''
),
cra AS (
    SELECT
        CAST(ano || '-01-01' AS DATE) AS competencia,
        clean_cnpj(cnpj_securitizadora) AS cnpj_emissor,
        UPPER(TRIM(codigo_isin)) AS codigo_isin,
        'cra' AS origem,
        nome_securitizadora AS nome_emissor,
        TRY_CAST(valor_emissao AS DECIMAL(20, 2)) AS valor_emissao
    FROM cvm.securitizacao_cra
    WHERE codigo_isin IS NOT NULL AND TRIM(codigo_isin) <> ''
),
consolidado AS (
    SELECT * FROM ofertas
    UNION ALL
    SELECT * FROM cri
    UNION ALL
    SELECT * FROM cra
),
indices_b3 AS (
    SELECT DISTINCT
        UPPER(TRIM(codigo_isin)) AS codigo_isin,
        TRUE AS em_indice_b3
    FROM b3.indices_carteiras
    WHERE codigo_isin IS NOT NULL AND TRIM(codigo_isin) <> ''
)
SELECT
    c.competencia,
    c.cnpj_emissor,
    c.codigo_isin,
    STRING_AGG(DISTINCT c.origem, '/') AS origem,
    MAX(c.nome_emissor) AS nome_emissor,
    SUM(c.valor_emissao) AS valor_emissao,
    COALESCE(bool_or(i.em_indice_b3), FALSE) AS match_instrumento
FROM consolidado c
LEFT JOIN indices_b3 i ON c.codigo_isin = i.codigo_isin
GROUP BY c.competencia, c.cnpj_emissor, c.codigo_isin
ORDER BY c.competencia, c.cnpj_emissor, c.codigo_isin;
