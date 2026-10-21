WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS SETOR_SUBSETOR_ID,
            DIM.D4N                                                 AS SETOR_SUBSETOR,
            DIM.D2N                                                 AS VARIAVEL,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '5932'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    SETOR_SUBSETOR_ID,
    SETOR_SUBSETOR,
    MAX(CASE WHEN VARIAVEL LIKE 'Taxa trimestral%'          THEN VALOR END) AS TAXA_TRIMESTRAL_MESMO_PERIODO,
    MAX(CASE WHEN VARIAVEL LIKE 'Taxa acumulada em quatro%' THEN VALOR END) AS TAXA_ACUM_4_TRIMESTRES,
    MAX(CASE WHEN VARIAVEL LIKE 'Taxa acumulada ao longo%'  THEN VALOR END) AS TAXA_ACUM_ANO,
    MAX(CASE WHEN VARIAVEL LIKE 'Taxa trimestre contra%'    THEN VALOR END) AS TAXA_QOQ
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    SETOR_SUBSETOR_ID,
    SETOR_SUBSETOR;
