SELECT marital_status, count(investor_id) AS investor_count
FROM td_investor
WHERE marital_status IS NOT NULL
GROUP BY marital_status
