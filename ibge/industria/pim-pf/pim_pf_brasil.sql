WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            D.TABELA_SIDRA_ID                                       AS TABELA_SIDRA_ID,
            CASE D.TABELA_SIDRA_ID
                WHEN '8885' THEN 'Grupos e classes industriais'
                WHEN '8886' THEN NULL
                WHEN '8887' THEN 'Grandes categorias econômicas'
                WHEN '8888' THEN 'Seções e atividades industriais (CNAE 2.0)'
                WHEN '8889' THEN 'Indicadores especiais'
            END                                                     AS TIPO_CLASSIFICACAO,
            CASE WHEN D.TABELA_SIDRA_ID != '8886' THEN DIM.D4C END AS CLASSIFICACAO_ID,
            CASE WHEN D.TABELA_SIDRA_ID != '8886' THEN DIM.D4N END AS CLASSIFICACAO,
            DIM.D2N                                                 AS VARIAVEL,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('8885', '8886', '8887', '8888', '8889')
            AND L.NC = '1'
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
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Número-índice (2022=100)'
             AND VARIAVEL NOT LIKE '%ajuste%'                       THEN VALOR END) AS NUMERO_INDICE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Número-índice com ajuste sazonal%'        THEN VALOR END) AS NUMERO_INDICE_SA,
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Variação mês/mês imediatamente anterior%' THEN VALOR END) AS VAR_MES_MES_ANTERIOR_SA,
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Variação mês/mesmo mês%'                  THEN VALOR END) AS VAR_MES_ANO_ANTERIOR,
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Variação acumulada no ano%'               THEN VALOR END) AS VAR_ACUM_ANO,
    MAX(CASE WHEN VARIAVEL LIKE 'PIMPF - Variação acumulada em 12 meses%'          THEN VALOR END) AS VAR_ACUM_12_MESES
FROM
    BASE
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
