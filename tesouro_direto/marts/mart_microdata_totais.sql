SELECT
    (SELECT count(*) FROM td_investor)                                          AS total_investors,
    (SELECT count(DISTINCT investor_id) FROM td_investidores
      WHERE account_status = 'A')                                               AS active_investors,
    (SELECT count(*) FROM td_operacoes)                                         AS total_operations
