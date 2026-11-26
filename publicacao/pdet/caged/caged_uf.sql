-- Novo CAGED por UF e competência: o que a UF tem de movimentação, na competência do evento.
-- Registros com UF fora do código IBGE ou competência inválida ficam de fora (ver
-- caged_uf_descartes.sql, que os conta).
WITH ufs(codigo, sigla) AS (
    VALUES ('11', 'RO'), ('12', 'AC'), ('13', 'AM'), ('14', 'RR'), ('15', 'PA'),
           ('16', 'AP'), ('17', 'TO'), ('21', 'MA'), ('22', 'PI'), ('23', 'CE'),
           ('24', 'RN'), ('25', 'PB'), ('26', 'PE'), ('27', 'AL'), ('28', 'SE'),
           ('29', 'BA'), ('31', 'MG'), ('32', 'ES'), ('33', 'RJ'), ('35', 'SP'),
           ('41', 'PR'), ('42', 'SC'), ('43', 'RS'), ('50', 'MS'), ('51', 'MT'),
           ('52', 'GO'), ('53', 'DF')
)
SELECT u.sigla AS entidade,
       make_date(CAST(substr(b.c, 1, 4) AS INTEGER), CAST(substr(b.c, 5, 2) AS INTEGER), 1) AS periodo,
       CAST(sum(b.adm) - sum(b.des) AS BIGINT) AS m_saldo,
       CAST(sum(b.adm) AS BIGINT) AS m_admissoes,
       CAST(sum(b.des) AS BIGINT) AS m_desligamentos
FROM base b
JOIN ufs u ON u.codigo = b.uf
WHERE regexp_matches(b.c, '^\d{4}(0[1-9]|1[0-2])$')
GROUP BY 1, 2
HAVING sum(b.adm) <> 0 OR sum(b.des) <> 0
ORDER BY 2, 1
