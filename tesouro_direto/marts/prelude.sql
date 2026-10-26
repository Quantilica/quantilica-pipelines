-- Preparação compartilhada pelos marts do Tesouro Direto (DuckDB sobre o lake).
-- As views do lake têm colunas de texto com nomes normalizados; a tipagem acontece aqui.

-- Meses truncados em UTC: é a convenção das tabelas servidas (mv_operations_monthly,
-- mv_investors_growth), independente do fuso da máquina que roda o mart.
SET TimeZone = 'UTC';

CREATE OR REPLACE MACRO td_date(x) AS
    COALESCE(
        TRY_STRPTIME(TRIM(x), '%d/%m/%Y'),
        TRY_STRPTIME(TRIM(x), '%d-%m-%Y'),
        TRY_STRPTIME(TRIM(x), '%Y-%m-%d')
    )::DATE;

-- Número no formato brasileiro (1.234,56). Texto fora do padrão vira NULL.
CREATE OR REPLACE MACRO td_decimal(x) AS
    CASE
        WHEN regexp_matches(replace(replace(TRIM(x), '.', ''), ',', '.'), '^-?[0-9]+(\.[0-9]+)?$')
        THEN CAST(replace(replace(TRIM(x), '.', ''), ',', '.') AS DECIMAL(18, 2))
    END;

CREATE OR REPLACE MACRO td_int(x) AS
    CASE WHEN regexp_matches(TRIM(x), '^[0-9]+$') THEN TRY_CAST(TRIM(x) AS INTEGER) END;

-- NULL cai no ELSE, como no CASE do PostgreSQL ('70+').
CREATE OR REPLACE MACRO td_age_range(age) AS
    CASE
        WHEN age <= 20 THEN '0-20'
        WHEN age <= 30 THEN '21-30'
        WHEN age <= 40 THEN '31-40'
        WHEN age <= 50 THEN '41-50'
        WHEN age <= 60 THEN '51-60'
        WHEN age <= 70 THEN '61-70'
        ELSE '70+'
    END;

CREATE OR REPLACE MACRO td_region(uf) AS
    CASE
        WHEN uf IN ('AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO') THEN 'Norte'
        WHEN uf IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE') THEN 'Nordeste'
        WHEN uf IN ('DF', 'GO', 'MS', 'MT') THEN 'Centro-Oeste'
        WHEN uf IN ('ES', 'MG', 'RJ', 'SP') THEN 'Sudeste'
        WHEN uf IN ('PR', 'RS', 'SC') THEN 'Sul'
        ELSE 'Outros'
    END;

CREATE OR REPLACE MACRO td_bond_canon(raw) AS
    CASE lower(TRIM(raw))
        WHEN 'tesouro renda+ aposentadoria extra' THEN 'Tesouro RendA+'
        WHEN 'tesouro renda+' THEN 'Tesouro RendA+'
        WHEN 'tesouro educa+' THEN 'Tesouro EducA+'
        WHEN 'tesouro selic' THEN 'Tesouro Selic'
        WHEN 'tesouro prefixado' THEN 'Tesouro Prefixado'
        WHEN 'tesouro prefixado com juros semestrais' THEN 'Tesouro Prefixado com Juros Semestrais'
        WHEN 'tesouro ipca+' THEN 'Tesouro IPCA+'
        WHEN 'tesouro ipca+ com juros semestrais' THEN 'Tesouro IPCA+ com Juros Semestrais'
        WHEN 'tesouro igpm+ com juros semestrais' THEN 'Tesouro IGPM+ com Juros Semestrais'
        ELSE TRIM(raw)
    END;

-- NTN-B1 vira RendA+ ou EducA+ conforme o vencimento (regra do importador).
CREATE OR REPLACE MACRO td_bond_type(raw, maturity) AS
    CASE
        WHEN upper(TRIM(td_bond_canon(raw))) = 'NTN-B1' THEN
            CASE
                WHEN maturity IS NOT NULL
                     AND month(maturity) = 12 AND day(maturity) = 15
                     AND year(maturity) >= 2049
                     AND (year(maturity) - 2049) % 5 = 0
                THEN 'Tesouro RendA+'
                ELSE 'Tesouro EducA+'
            END
        ELSE td_bond_canon(raw)
    END;

-- Linhas dos arquivos de investidores, tipadas. Os arquivos são anuais: o ano do
-- nome do arquivo ordena as versões de cada investidor.
CREATE OR REPLACE VIEW td_investidores AS
SELECT
    td_int(codigo_do_investidor)                    AS investor_id,
    td_date(data_de_adesao)                         AS join_date,
    NULLIF(TRIM(estado_civil), '')                  AS marital_status,
    NULLIF(TRIM(genero), '')                        AS gender,
    NULLIF(TRIM(profissao), '')                     AS profession,
    CASE WHEN regexp_matches(TRIM(idade_do_investidor), '^[0-9]+$')
         THEN TRY_CAST(TRIM(idade_do_investidor) AS SMALLINT) END AS age,
    NULLIF(TRIM(uf_do_investidor), '')              AS state,
    NULLIF(TRIM(situacao_da_conta), '')             AS account_status,
    NULLIF(TRIM(operou_12_meses), '')               AS traded_last_12_months,
    TRY_CAST(regexp_extract(_arquivo, '([0-9]{4})\.parquet$', 1) AS INTEGER) AS file_year
FROM tesouro_direto.investidores
WHERE td_int(codigo_do_investidor) IS NOT NULL;

-- Operações válidas (mesmos descartes do importador).
CREATE OR REPLACE VIEW td_operacoes AS
WITH base AS (
    SELECT
        td_int(codigo_do_investidor)                AS investor_id,
        td_date(data_da_operacao)                   AS operation_date,
        td_date(vencimento_do_titulo)               AS maturity_date,
        tipo_titulo                                 AS raw_bond_type,
        td_decimal(valor_da_operacao)               AS operation_value,
        COALESCE(tipo_da_operacao, '')              AS operation_type
    FROM tesouro_direto.operacoes
)
SELECT
    investor_id,
    operation_date,
    maturity_date,
    td_bond_type(raw_bond_type, maturity_date)      AS bond_type,
    operation_value,
    operation_type
FROM base
WHERE investor_id IS NOT NULL
  AND operation_date IS NOT NULL
  AND maturity_date IS NOT NULL
  AND td_bond_type(raw_bond_type, maturity_date) IS NOT NULL
  AND td_bond_type(raw_bond_type, maturity_date) <> '';

-- Um registro por investidor: o último valor não nulo de cada atributo, na ordem
-- dos arquivos. Investidores que só aparecem em operações entram com atributos NULL.
CREATE OR REPLACE VIEW td_investor AS
WITH ids AS (
    SELECT investor_id FROM td_investidores
    UNION
    SELECT investor_id FROM td_operacoes
),
attrs AS (
    SELECT
        investor_id,
        arg_max(marital_status, file_year) FILTER (WHERE marital_status IS NOT NULL) AS marital_status,
        arg_max(gender, file_year)         FILTER (WHERE gender IS NOT NULL)         AS gender,
        arg_max(profession, file_year)     FILTER (WHERE profession IS NOT NULL)     AS profession,
        arg_max(age, file_year)            FILTER (WHERE age IS NOT NULL)            AS age,
        arg_max(state, file_year)          FILTER (WHERE state IS NOT NULL)          AS state
    FROM td_investidores
    GROUP BY investor_id
)
SELECT ids.investor_id, a.marital_status, a.gender, a.profession, a.age, a.state
FROM ids
LEFT JOIN attrs a USING (investor_id);
