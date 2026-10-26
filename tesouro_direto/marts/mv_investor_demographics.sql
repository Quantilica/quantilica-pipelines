-- Reproduz a definição anterior: NULL de idade cai em '70+'.
SELECT gender, td_age_range(age) AS age_range, count(*) AS investor_count
FROM td_investor
GROUP BY gender, td_age_range(age)
