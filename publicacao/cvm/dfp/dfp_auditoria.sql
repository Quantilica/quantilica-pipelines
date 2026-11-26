-- Auditoria do desempate das cópias divergentes (ver `dfp_cia.sql`): não é dado servido, só o que o
-- carregador conta e imprime. Uma linha por achado, com as colunas `tipo`, `chave` e `detalhe`:
--   ambigua            célula (companhia, exercício, conta, demonstração) que continuou com mais
--                      de um valor EMPATADO em número de cópias e sem correção (o maior valor
--                      foi o escolhido): precisa de uma linha em `correcoes.csv`;
--   correcao_aplicada  correção que valeu (a célula tem mais de um valor e o oficial é um deles);
--   correcao_sem_efeito correção que não valeu, com o motivo (a CVM limpou o arquivo, o valor
--                      oficial não está entre as cópias ou a célula saiu da seleção).
-- A seleção é a mesma de `dfp_cia.sql`: último encerramento do ano, consolidada se existir,
-- versão mais nova da conta.
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
), na_selecao AS (
    SELECT r.cnpj, r.exercicio, r.conta, r.tipo, r.versao, r.valor
    FROM do_encerramento r
    JOIN tipo_do_exercicio t USING (cnpj, exercicio)
    WHERE (r.tipo = 'C') = t.consolidada
), por_valor AS (
    SELECT cnpj, exercicio, conta, tipo, valor, count(*) AS copias
    FROM (
        SELECT *, versao = max(versao) OVER (PARTITION BY cnpj, exercicio, conta) AS ok
        FROM na_selecao
    )
    WHERE ok AND valor IS NOT NULL
    GROUP BY cnpj, exercicio, conta, tipo, valor
), celulas AS (
    SELECT cnpj, exercicio, conta, tipo,
           count(*) AS distintos,
           list(valor ORDER BY valor) AS valores,
           count(*) FILTER (WHERE copias = maximo) AS empatados
    FROM (
        SELECT *, max(copias) OVER (PARTITION BY cnpj, exercicio, conta, tipo) AS maximo
        FROM por_valor
    )
    GROUP BY cnpj, exercicio, conta, tipo
), com_correcao AS (
    SELECT k.*, c.distintos, c.valores,
           CASE WHEN c.cnpj IS NULL THEN 'a célula não está na seleção (companhia, exercício, conta ou demonstração sem valor no lake)'
                WHEN c.distintos < 2 THEN 'a CVM não deixou mais de um valor nesta célula (arquivo limpo?)'
                WHEN len(list_filter(c.valores, lambda x: abs(x - k.valor) < 0.005)) = 0
                     THEN 'o valor oficial não está entre as cópias do lake'
           END AS motivo_sem_efeito
    FROM correcoes k
    LEFT JOIN celulas c
           ON c.cnpj = k.cnpj AND CAST(c.exercicio AS VARCHAR) = k.exercicio
          AND c.conta = k.medida
          AND k.demonstracao = CASE c.tipo WHEN 'C' THEN 'consolidada' ELSE 'individual' END
), rotulo AS (
    SELECT cnpj, exercicio, conta, tipo,
           cnpj || ' ' || exercicio || ' ' || conta || ' '
               || CASE tipo WHEN 'C' THEN 'consolidada' ELSE 'individual' END AS chave
    FROM celulas
)
SELECT 'ambigua' AS tipo, r.chave AS chave,
       'valores empatados: ' || array_to_string(list_transform(c.valores, lambda x: CAST(CAST(x AS BIGINT) AS VARCHAR)), ' / ') AS detalhe
FROM celulas c
JOIN rotulo r USING (cnpj, exercicio, conta, tipo)
WHERE c.empatados > 1
  AND NOT EXISTS (
      SELECT 1 FROM com_correcao k
      WHERE k.cnpj = c.cnpj AND k.exercicio = CAST(c.exercicio AS VARCHAR) AND k.medida = c.conta
        AND k.demonstracao = CASE c.tipo WHEN 'C' THEN 'consolidada' ELSE 'individual' END
        AND k.motivo_sem_efeito IS NULL)
UNION ALL
SELECT 'correcao_aplicada', k.cnpj || ' ' || k.exercicio || ' ' || k.medida || ' ' || k.demonstracao,
       'valor oficial ' || CAST(CAST(k.valor AS BIGINT) AS VARCHAR) || ' (' || k.referencia || ')'
FROM com_correcao k
WHERE k.motivo_sem_efeito IS NULL
UNION ALL
SELECT 'correcao_sem_efeito', k.cnpj || ' ' || k.exercicio || ' ' || k.medida || ' ' || k.demonstracao,
       k.motivo_sem_efeito
FROM com_correcao k
WHERE k.motivo_sem_efeito IS NOT NULL
ORDER BY 1, 2
