WITH
	SINAPI AS (
		SELECT
			P.DATA_INICIO AS PERIODO,
			L.NC AS ID_NIVEL_LOCALIDADE,
			L.NN AS NOME_NIVEL_LOCALIDADE,
			L.D1C AS ID_LOCALIDADE,
			L.D1N AS NOME_LOCALIDADE,
			CASE D.TABELA_SIDRA_ID
				WHEN '2296' THEN 'Com desoneração'
				WHEN '6586' THEN 'Sem desoneração'
			END AS MODALIDADE,
			REPLACE(
				DIM.D2N,
				', sem desoneração da folha de pagamento',
				''
			) AS VARIAVEL,
			DIM.MN AS UNIDADE,
			CASE
				WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC
			END AS VALOR
		FROM
			DADOS D
			JOIN PERIODO P ON D.PERIODO_ID = P.ID
			JOIN DIMENSAO DIM ON D.DIMENSAO_ID = DIM.ID
			JOIN LOCALIDADE L ON D.LOCALIDADE_ID = L.ID
		WHERE
			D.TABELA_SIDRA_ID IN ('2296', '6586')
			AND D.ATIVO = TRUE
	)
SELECT
	PERIODO,
	ID_NIVEL_LOCALIDADE,
	NOME_NIVEL_LOCALIDADE,
	ID_LOCALIDADE,
	NOME_LOCALIDADE,
	MODALIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente mão-de-obra - moeda corrente' THEN VALOR
			ELSE NULL
		END
	) AS MAO_DE_OBRA_MOEDA_CORRENTE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente mão-de-obra - moeda corrente' THEN UNIDADE
		END
	) AS MAO_DE_OBRA_MOEDA_CORRENTE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente mão-de-obra - número-índice' THEN VALOR
			ELSE NULL
		END
	) AS MAO_DE_OBRA_NUMERO_INDICE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente mão-de-obra - número-índice' THEN UNIDADE
		END
	) AS MAO_DE_OBRA_NUMERO_INDICE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente material - moeda corrente' THEN VALOR
			ELSE NULL
		END
	) AS MATERIAL_MOEDA_CORRENTE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente material - moeda corrente' THEN UNIDADE
		END
	) AS MATERIAL_MOEDA_CORRENTE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente material - número-índice' THEN VALOR
			ELSE NULL
		END
	) AS MATERIAL_NUMERO_INDICE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - componente material - número-índice' THEN UNIDADE
		END
	) AS MATERIAL_NUMERO_INDICE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - moeda corrente' THEN VALOR
			ELSE NULL
		END
	) AS CUSTO_TOTAL_MOEDA_CORRENTE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - moeda corrente' THEN UNIDADE
		END
	) AS CUSTO_TOTAL_MOEDA_CORRENTE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - número-índice' THEN VALOR
			ELSE NULL
		END
	) AS CUSTO_TOTAL_NUMERO_INDICE,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - número-índice' THEN UNIDADE
		END
	) AS CUSTO_TOTAL_NUMERO_INDICE_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual em doze meses' THEN VALOR
			ELSE NULL
		END
	) AS VARIACAO_DOZE_MESES,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual em doze meses' THEN UNIDADE
		END
	) AS VARIACAO_DOZE_MESES_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual no ano' THEN VALOR
			ELSE NULL
		END
	) AS VARIACAO_ANO,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual no ano' THEN UNIDADE
		END
	) AS VARIACAO_ANO_UNIDADE,
	SUM(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual no mês' THEN VALOR
			ELSE NULL
		END
	) AS VARIACAO_MES,
	MAX(
		CASE
			WHEN VARIAVEL = 'Custo médio m² - variação percentual no mês' THEN UNIDADE
		END
	) AS VARIACAO_MES_UNIDADE
FROM
	SINAPI
GROUP BY
	PERIODO,
	ID_NIVEL_LOCALIDADE,
	NOME_NIVEL_LOCALIDADE,
	ID_LOCALIDADE,
	NOME_LOCALIDADE,
	MODALIDADE;
