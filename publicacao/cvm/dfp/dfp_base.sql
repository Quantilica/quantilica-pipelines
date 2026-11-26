-- Contas principais da DFP, uma linha por (companhia, encerramento, conta, tipo, versão).
-- Os valores vêm em `ESCALA_MOEDA` MIL ou UNIDADE e saem em reais. Só a última coluna de
-- exercício (`ÚLTIMO`) e só moeda REAL. Os códigos mudam por setor; por isso o patrimônio
-- líquido e o lucro líquido também pela descrição da conta.
-- tipo: C = demonstração consolidada, I = individual (pelo nome do arquivo).
SELECT regexp_replace(CNPJ_CIA, '\D', '', 'g') AS cnpj,
       CAST(DT_REFER AS DATE) AS encerramento,
       'ativo_total' AS conta,
       CASE WHEN regexp_matches(filename, '_con_\d{4}\.parquet$') THEN 'C' ELSE 'I' END AS tipo,
       VERSAO AS versao, CD_CVM AS cd_cvm, DENOM_CIA AS nome,
       try_cast(VL_CONTA AS DOUBLE) * (CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END) AS valor
FROM read_parquet($bpa, union_by_name = true, filename = true)
WHERE ORDEM_EXERC = 'ÚLTIMO' AND MOEDA = 'REAL' AND CD_CONTA = '1'
UNION ALL
SELECT regexp_replace(CNPJ_CIA, '\D', '', 'g'), CAST(DT_REFER AS DATE),
       'patrimonio_liquido',
       CASE WHEN regexp_matches(filename, '_con_\d{4}\.parquet$') THEN 'C' ELSE 'I' END,
       VERSAO, CD_CVM, DENOM_CIA,
       try_cast(VL_CONTA AS DOUBLE) * (CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END)
FROM read_parquet($bpp, union_by_name = true, filename = true)
WHERE ORDEM_EXERC = 'ÚLTIMO' AND MOEDA = 'REAL'
  AND regexp_matches(CD_CONTA, '^2\.0\d$') AND DS_CONTA ILIKE 'Patrimônio Líquido%'
UNION ALL
SELECT regexp_replace(CNPJ_CIA, '\D', '', 'g'), CAST(DT_REFER AS DATE),
       'receita',
       CASE WHEN regexp_matches(filename, '_con_\d{4}\.parquet$') THEN 'C' ELSE 'I' END,
       VERSAO, CD_CVM, DENOM_CIA,
       try_cast(VL_CONTA AS DOUBLE) * (CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END)
FROM read_parquet($dre, union_by_name = true, filename = true)
WHERE ORDEM_EXERC = 'ÚLTIMO' AND MOEDA = 'REAL' AND CD_CONTA = '3.01'
UNION ALL
SELECT regexp_replace(CNPJ_CIA, '\D', '', 'g'), CAST(DT_REFER AS DATE),
       'lucro_liquido',
       CASE WHEN regexp_matches(filename, '_con_\d{4}\.parquet$') THEN 'C' ELSE 'I' END,
       VERSAO, CD_CVM, DENOM_CIA,
       try_cast(VL_CONTA AS DOUBLE) * (CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END)
FROM read_parquet($dre, union_by_name = true, filename = true)
WHERE ORDEM_EXERC = 'ÚLTIMO' AND MOEDA = 'REAL'
  AND regexp_matches(CD_CONTA, '^3\.\d\d$') AND DS_CONTA ILIKE '%do Período'
  AND DS_CONTA NOT ILIKE 'Lucro por Ação%'
UNION ALL
SELECT regexp_replace(CNPJ_CIA, '\D', '', 'g'), CAST(DT_REFER AS DATE),
       'caixa_operacional',
       CASE WHEN regexp_matches(filename, '_con_\d{4}\.parquet$') THEN 'C' ELSE 'I' END,
       VERSAO, CD_CVM, DENOM_CIA,
       try_cast(VL_CONTA AS DOUBLE) * (CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END)
FROM read_parquet($dfc, union_by_name = true, filename = true)
WHERE ORDEM_EXERC = 'ÚLTIMO' AND MOEDA = 'REAL' AND CD_CONTA = '6.01'
