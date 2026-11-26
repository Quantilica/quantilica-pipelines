-- O que o CAGED por UF deixa de fora: competência inválida ou UF fora do código IBGE.
-- Entra em carga.detalhes como auditoria; admissões e desligamentos, não o saldo.
WITH ufs(codigo, sigla) AS (
    VALUES ('11', 'RO'), ('12', 'AC'), ('13', 'AM'), ('14', 'RR'), ('15', 'PA'),
           ('16', 'AP'), ('17', 'TO'), ('21', 'MA'), ('22', 'PI'), ('23', 'CE'),
           ('24', 'RN'), ('25', 'PB'), ('26', 'PE'), ('27', 'AL'), ('28', 'SE'),
           ('29', 'BA'), ('31', 'MG'), ('32', 'ES'), ('33', 'RJ'), ('35', 'SP'),
           ('41', 'PR'), ('42', 'SC'), ('43', 'RS'), ('50', 'MS'), ('51', 'MT'),
           ('52', 'GO'), ('53', 'DF')
)
SELECT CASE WHEN regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$')
            THEN substr(b.c, 1, 4) || '-' || substr(b.c, 5, 2)
            ELSE 'invalida' END AS periodo,
       CAST(sum(b.adm) AS BIGINT) AS m_admissoes,
       CAST(sum(b.des) AS BIGINT) AS m_desligamentos
FROM base b
LEFT JOIN ufs u ON u.codigo = b.uf
WHERE u.sigla IS NULL
   OR NOT coalesce(regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$'), false)
GROUP BY 1
ORDER BY 1
