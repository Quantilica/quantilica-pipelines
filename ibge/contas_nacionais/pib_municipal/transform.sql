WITH
	BASE AS (
		SELECT
			P.ANO AS ANO,
			L.D1C AS ID_MUNICIPIO,
			L.D1N AS NOME_MUNICIPIO,
			DIM.D2N AS VARIAVEL,
			CASE
				WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC
			END AS VALOR
		FROM
			DADOS D
			JOIN PERIODO P ON D.PERIODO_ID = P.ID
			JOIN DIMENSAO DIM ON D.DIMENSAO_ID = DIM.ID
			JOIN LOCALIDADE L ON D.LOCALIDADE_ID = L.ID
		WHERE
			D.TABELA_SIDRA_ID = '5938'
			AND D.ATIVO = TRUE
	)
SELECT
	ANO,
	ID_MUNICIPIO,
	NOME_MUNICIPIO,
	MAX(CASE WHEN VARIAVEL = 'Produto Interno Bruto a preços correntes'                                THEN VALOR END) AS PIB,
	MAX(CASE WHEN VARIAVEL = 'Impostos, líquidos de subsídios, sobre produtos a preços correntes'     THEN VALOR END) AS IMPOSTOS_LIQUIDOS_SUBSIDIOS,
	MAX(CASE WHEN VARIAVEL = 'Valor adicionado bruto a preços correntes total'                        THEN VALOR END) AS VAB_TOTAL,
	MAX(CASE WHEN VARIAVEL = 'Valor adicionado bruto a preços correntes da agropecuária'              THEN VALOR END) AS VAB_AGROPECUARIA,
	MAX(CASE WHEN VARIAVEL = 'Valor adicionado bruto a preços correntes da indústria'                 THEN VALOR END) AS VAB_INDUSTRIA,
	MAX(CASE WHEN VARIAVEL LIKE 'Valor adicionado bruto a preços correntes dos serviços%'             THEN VALOR END) AS VAB_SERVICOS,
	MAX(CASE WHEN VARIAVEL LIKE 'Valor adicionado bruto a preços correntes da administração%'         THEN VALOR END) AS VAB_ADMINISTRACAO_SAUDE
FROM
	BASE
GROUP BY
	ANO,
	ID_MUNICIPIO,
	NOME_MUNICIPIO;
