-- Tabela 254: estoque por produto, tipo de propriedade e tipo de atividade
-- Tabela 255: estoque por produto (sem desagregação por propriedade/atividade)
WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            D.TABELA_SIDRA_ID                                       AS TABELA_SIDRA_ID,
            DIM.D4C                                                 AS PRODUTO_ID,
            DIM.D4N                                                 AS PRODUTO,
            CASE WHEN D.TABELA_SIDRA_ID = '254' THEN DIM.D5C END   AS TIPO_PROPRIEDADE_ID,
            CASE WHEN D.TABELA_SIDRA_ID = '254' THEN DIM.D5N END   AS TIPO_PROPRIEDADE,
            CASE WHEN D.TABELA_SIDRA_ID = '254' THEN DIM.D6C END   AS TIPO_ATIVIDADE_ID,
            CASE WHEN D.TABELA_SIDRA_ID = '254' THEN DIM.D6N END   AS TIPO_ATIVIDADE,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('254', '255')
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    PRODUTO_ID,
    PRODUTO,
    TIPO_PROPRIEDADE_ID,
    TIPO_PROPRIEDADE,
    TIPO_ATIVIDADE_ID,
    TIPO_ATIVIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                        THEN VALOR   END) AS NUMERO_INFORMANTES,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                        THEN UNIDADE END) AS NUMERO_INFORMANTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes - percentual do total geral' THEN VALOR END) AS NUMERO_INFORMANTES_PCT,
    MAX(CASE WHEN VARIAVEL = 'Quantidade estocada'                          THEN VALOR   END) AS QUANTIDADE_ESTOCADA,
    MAX(CASE WHEN VARIAVEL = 'Quantidade estocada'                          THEN UNIDADE END) AS QUANTIDADE_ESTOCADA_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Quantidade estocada - percentual do total geral' THEN VALOR END) AS QUANTIDADE_ESTOCADA_PCT,
    MAX(CASE WHEN VARIAVEL = 'Número de municípios'                         THEN VALOR   END) AS NUMERO_MUNICIPIOS,
    MAX(CASE WHEN VARIAVEL = 'Estoque no último dia do semestre'            THEN VALOR   END) AS ESTOQUE,
    MAX(CASE WHEN VARIAVEL = 'Estoque no último dia do semestre'            THEN UNIDADE END) AS ESTOQUE_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    PRODUTO_ID,
    PRODUTO,
    TIPO_PROPRIEDADE_ID,
    TIPO_PROPRIEDADE,
    TIPO_ATIVIDADE_ID,
    TIPO_ATIVIDADE;
