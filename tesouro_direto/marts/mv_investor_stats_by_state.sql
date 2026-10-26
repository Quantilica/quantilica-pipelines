SELECT state, count(DISTINCT investor_id) AS total_investors
FROM td_investor
WHERE state IS NOT NULL
GROUP BY state
