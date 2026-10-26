SELECT marital_status, gender, count(investor_id) AS investor_count
FROM td_investor
WHERE marital_status IS NOT NULL AND gender IS NOT NULL
GROUP BY marital_status, gender
