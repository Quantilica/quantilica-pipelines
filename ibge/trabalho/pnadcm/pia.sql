-- Tabelas com classificação (D4):
--   6318 → Condição em relação à força de trabalho e condição de ocupação
--   6438 → Tipo de medida de subutilização da força de trabalho na semana de referência
-- Tabelas sem classificação (D4 = NULL):
--   5944, 6379, 6380, 6381, 6439, 6440, 6441, 6807
-- Tabelas com variações absoluta (TYPE A): 6318, 6438
-- Tabelas somente com variações simples (TYPE B): 5944, 6379, 6380, 6381, 6439, 6440, 6441, 6807
WITH
    BASE AS (
        SELECT
            P.DATA_INICIO AS PERIODO,
            L.NC          AS NIVEL_TERRITORIAL_ID,
            L.NN          AS NIVEL_TERRITORIAL,
            L.D1C         AS LOCALIDADE_ID,
            L.D1N         AS LOCALIDADE,
            D.TABELA_SIDRA_ID,
            CASE D.TABELA_SIDRA_ID
                WHEN '6318' THEN 'Condição em relação à força de trabalho e condição de ocupação'
                WHEN '6438' THEN 'Tipo de medida de subutilização da força de trabalho na semana de referência'
            END                                                        AS TIPO_CLASSIFICACAO,
            CASE WHEN D.TABELA_SIDRA_ID IN ('6318', '6438') THEN DIM.D4C END AS CLASSIFICACAO_ID,
            CASE WHEN D.TABELA_SIDRA_ID IN ('6318', '6438') THEN DIM.D4N END AS CLASSIFICACAO,
            DIM.D2N       AS VARIAVEL,
            DIM.MN        AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END AS VALOR,
            D.V           AS VALOR_TEXTO
        FROM
            DADOS D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN (
                '6318', '5944', '6379', '6380', '6381',
                '6438', '6439', '6440', '6441', '6807'
            )
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    TIPO_CLASSIFICACAO,
    CLASSIFICACAO_ID,
    CLASSIFICACAO,
    -- Valor principal
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'     THEN VALOR       END) AS VALOR,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'     THEN UNIDADE     END) AS VALOR_UNIDADE,
    -- Coeficiente de variação
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'      THEN VALOR       END) AS CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'      THEN UNIDADE     END) AS CV_UNIDADE,
    -- Variação em relação aos 3 trimestres móveis anteriores
    -- TYPE A: "Variação percentual em relação a três..." | TYPE B: "Variação em relação a três..."
    MAX(CASE WHEN (VARIAVEL LIKE 'Variação percentual em relação a três%'
               OR  VARIAVEL LIKE 'Variação em relação a três%')         THEN VALOR   END) AS VAR_3TM,
    MAX(CASE WHEN (VARIAVEL LIKE 'Variação percentual em relação a três%'
               OR  VARIAVEL LIKE 'Variação em relação a três%')         THEN UNIDADE END) AS VAR_3TM_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'  THEN VALOR   END) AS VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'  THEN UNIDADE END) AS VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%' THEN VALOR_TEXTO END) AS VAR_3TM_SIT,
    -- Variação em relação ao mesmo trimestre móvel do ano anterior
    MAX(CASE WHEN (VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
               OR  VARIAVEL LIKE 'Variação em relação ao mesmo%')       THEN VALOR   END) AS VAR_ANO,
    MAX(CASE WHEN (VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
               OR  VARIAVEL LIKE 'Variação em relação ao mesmo%')       THEN UNIDADE END) AS VAR_ANO_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%' THEN VALOR   END) AS VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%' THEN UNIDADE END) AS VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%' THEN VALOR_TEXTO END) AS VAR_ANO_SIT
FROM BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    TIPO_CLASSIFICACAO,
    CLASSIFICACAO_ID,
    CLASSIFICACAO;
