-- Tabelas com real + nominal (16 variáveis):
--   6390 → rendimento médio habitual, todos os trabalhos
--   6387 → rendimento médio efetivo, todos os trabalhos
-- Tabelas com apenas real (8 variáveis):
--   6389 → rendimento médio habitual, trabalho principal — por posição na ocupação (D4)
--   6388 → rendimento médio efetivo, trabalho principal
--   6391 → rendimento médio habitual, trabalho principal — por grupamento de atividade (D4)
-- Colunas nominais são NULL para 6388, 6389 e 6391 (IBGE só divulga real nesses casos)
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
                WHEN '6389' THEN 'Posição na ocupação e categoria do emprego no trabalho principal'
                WHEN '6391' THEN 'Grupamento de atividade no trabalho principal'
            END                                                            AS TIPO_CLASSIFICACAO,
            CASE WHEN D.TABELA_SIDRA_ID IN ('6389', '6391') THEN DIM.D4C END AS CLASSIFICACAO_ID,
            CASE WHEN D.TABELA_SIDRA_ID IN ('6389', '6391') THEN DIM.D4N END AS CLASSIFICACAO,
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
            D.TABELA_SIDRA_ID IN ('6390', '6387', '6389', '6388', '6391')
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
    -- Rendimento real
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL_CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_CV_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL_VAR_3TM_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_VAR_3TM_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL_VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR_TEXTO END) AS RENDIMENTO_REAL_VAR_3TM_SIT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL_VAR_ANO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_VAR_ANO_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS RENDIMENTO_REAL_VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS RENDIMENTO_REAL_VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR_TEXTO END) AS RENDIMENTO_REAL_VAR_ANO_SIT,
    -- Rendimento nominal (apenas 6390 e 6387; NULL para 6388, 6389, 6391)
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL_CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_CV_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL_VAR_3TM_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_VAR_3TM_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL_VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR_TEXTO END) AS RENDIMENTO_NOMINAL_VAR_3TM_SIT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL_VAR_ANO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_VAR_ANO_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS RENDIMENTO_NOMINAL_VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS RENDIMENTO_NOMINAL_VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR_TEXTO END) AS RENDIMENTO_NOMINAL_VAR_ANO_SIT
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
