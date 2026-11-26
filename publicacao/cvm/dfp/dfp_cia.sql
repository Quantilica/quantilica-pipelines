-- DFP por companhia (CNPJ sem pontuação) e exercício social, uma linha por par, com as cinco
-- contas em colunas.
-- `exercicio` é o ano do encerramento do exercício (nem todo exercício fecha em 31/12). Se a
-- companhia tem dois encerramentos no mesmo ano (mudou o fim do exercício), fica o mais
-- recente; dentro dele, a demonstração consolidada se existir e, em cada conta, a versão mais
-- nova (duas linhas da mesma versão com valores diferentes: fica o maior, para a carga ser
-- repetível). Nome e código CVM são os do exercício mais recente da companhia.
WITH com_exercicio AS (
    SELECT *, year(encerramento) AS exercicio
    FROM base
    WHERE encerramento IS NOT NULL
), ultimo_encerramento AS (
    SELECT cnpj, exercicio, max(encerramento) AS encerramento
    FROM com_exercicio GROUP BY 1, 2
), do_encerramento AS (
    SELECT b.*
    FROM com_exercicio b
    JOIN ultimo_encerramento u USING (cnpj, exercicio, encerramento)
), tipo_do_exercicio AS (
    SELECT cnpj, exercicio, bool_or(tipo = 'C') AS consolidada
    FROM do_encerramento GROUP BY 1, 2
), escolhidas AS (
    SELECT r.*, t.consolidada,
           row_number() OVER (PARTITION BY r.cnpj, r.exercicio, r.conta
                              ORDER BY r.versao DESC, r.valor DESC) AS rn
    FROM do_encerramento r
    JOIN tipo_do_exercicio t USING (cnpj, exercicio)
    WHERE (r.tipo = 'C') = t.consolidada
), recente AS (
    SELECT cnpj, arg_max(nome, encerramento) AS nome, arg_max(cd_cvm, encerramento) AS cd_cvm
    FROM escolhidas GROUP BY 1
)
SELECT e.cnpj AS entidade,
       coalesce(r.nome, '') AS entidade_rotulo,
       r.cd_cvm AS entidade_cd_cvm,
       make_date(e.exercicio, 1, 1) AS periodo,
       bool_or(e.consolidada) AS a_consolidado,
       max(e.encerramento) AS a_encerramento,
       max(e.valor) FILTER (WHERE e.conta = 'ativo_total') AS m_ativo_total,
       max(e.valor) FILTER (WHERE e.conta = 'patrimonio_liquido') AS m_patrimonio_liquido,
       max(e.valor) FILTER (WHERE e.conta = 'receita') AS m_receita,
       max(e.valor) FILTER (WHERE e.conta = 'lucro_liquido') AS m_lucro_liquido,
       max(e.valor) FILTER (WHERE e.conta = 'caixa_operacional') AS m_caixa_operacional
FROM escolhidas e
JOIN recente r USING (cnpj)
WHERE e.rn = 1 AND e.cnpj <> '' AND length(e.cnpj) = 14
GROUP BY e.cnpj, r.nome, r.cd_cvm, e.exercicio
ORDER BY e.exercicio, e.cnpj
