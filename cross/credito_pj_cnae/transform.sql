-- cross.mart_credito_pj_cnae
-- Agrega operações de crédito PJ do SCR por divisão de CNAE e modalidade.

WITH scr_agregado AS (
    SELECT
        CAST(SUBSTR(CAST(data_base AS VARCHAR), 1, 7) || '-01' AS DATE) AS competencia,
        LPAD(TRIM(cnae_divisao), 2, '0') AS cnae_divisao,
        TRIM(modalidade) AS modalidade,
        COUNT(*) AS total_operacoes,
        SUM(TRY_CAST(valor_carteira AS DECIMAL(20, 2))) AS valor_total_carteira
    FROM bcb_microdados.scr_carteira_cnae_rating
    WHERE cnae_divisao IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT
    competencia,
    cnae_divisao,
    modalidade,
    total_operacoes,
    valor_total_carteira
FROM scr_agregado
ORDER BY competencia, cnae_divisao, modalidade;
