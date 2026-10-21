WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS REFERENCIA_TEMPORAL_ID,
            DIM.D4N                                                 AS REFERENCIA_TEMPORAL,
            DIM.D5C                                                 AS FINALIDADE_PRODUCAO_ID,
            DIM.D5N                                                 AS FINALIDADE_PRODUCAO,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '7524'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    REFERENCIA_TEMPORAL_ID,
    REFERENCIA_TEMPORAL,
    FINALIDADE_PRODUCAO_ID,
    FINALIDADE_PRODUCAO,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                          THEN VALOR   END) AS NUMERO_INFORMANTES,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                          THEN UNIDADE END) AS NUMERO_INFORMANTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes - percentual do total geral'                              THEN VALOR   END) AS NUMERO_INFORMANTES_PCT,
    MAX(CASE WHEN VARIAVEL = 'Número de cabeças de galinhas poedeiras nos estabelecimentos agropecuários'    THEN VALOR   END) AS CABECAS_GALINHAS_POEDEIRAS,
    MAX(CASE WHEN VARIAVEL = 'Número de cabeças de galinhas poedeiras nos estabelecimentos agropecuários'    THEN UNIDADE END) AS CABECAS_GALINHAS_POEDEIRAS_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Quantidade de ovos produzidos'                                                  THEN VALOR   END) AS OVOS_PRODUZIDOS,
    MAX(CASE WHEN VARIAVEL = 'Quantidade de ovos produzidos'                                                  THEN UNIDADE END) AS OVOS_PRODUZIDOS_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Quantidade de ovos produzidos - percentual do total geral'                      THEN VALOR   END) AS OVOS_PRODUZIDOS_PCT
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    REFERENCIA_TEMPORAL_ID,
    REFERENCIA_TEMPORAL,
    FINALIDADE_PRODUCAO_ID,
    FINALIDADE_PRODUCAO;
