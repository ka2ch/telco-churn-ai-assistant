-- Churn pattern analysis
-- Each query starts with "-- name:" so src/run_analysis.py can run them one by one.
-- churned: 1 = left, 0 = stayed. AVG(churned) * 100 = churn rate in %.


-- name: 1. Overall churn rate
SELECT COUNT(*)                        AS customers,
       SUM(churned)                    AS churned,
       ROUND(AVG(churned) * 100, 1)    AS churn_rate_pct
FROM customers;


-- name: 2. Churn by how long they have been a customer
SELECT CASE
           WHEN tenure_months <= 12 THEN '1) 0-12 months'
           WHEN tenure_months <= 24 THEN '2) 13-24 months'
           WHEN tenure_months <= 48 THEN '3) 25-48 months'
           ELSE                          '4) 49+ months'
       END                             AS tenure_group,
       COUNT(*)                        AS customers,
       ROUND(AVG(churned) * 100, 1)    AS churn_rate_pct
FROM customers
GROUP BY tenure_group
ORDER BY tenure_group;


-- name: 3. Churn by internet service type
SELECT s.internet_service,
       COUNT(*)                          AS customers,
       ROUND(AVG(c.churned) * 100, 1)    AS churn_rate_pct
FROM customers c
JOIN services s ON c.customer_id = s.customer_id
GROUP BY s.internet_service
ORDER BY churn_rate_pct DESC;


-- name: 4. Churn by payment method
SELECT b.payment_method,
       COUNT(*)                          AS customers,
       ROUND(AVG(c.churned) * 100, 1)    AS churn_rate_pct
FROM customers c
JOIN billing b ON c.customer_id = b.customer_id
GROUP BY b.payment_method
ORDER BY churn_rate_pct DESC;


-- name: 5. Does tech support / online security keep internet customers?
SELECT CASE WHEN s.tech_support = 1    THEN 'Yes' ELSE 'No' END AS tech_support,
       CASE WHEN s.online_security = 1 THEN 'Yes' ELSE 'No' END AS online_security,
       COUNT(*)                          AS customers,
       ROUND(AVG(c.churned) * 100, 1)    AS churn_rate_pct
FROM customers c
JOIN services s ON c.customer_id = s.customer_id
WHERE s.internet_service <> 'No'
GROUP BY s.tech_support, s.online_security
ORDER BY churn_rate_pct DESC;


-- name: 6. Monthly bill: customers who left vs stayed
SELECT CASE WHEN c.churned = 1 THEN 'Left' ELSE 'Stayed' END AS status,
       COUNT(*)                          AS customers,
       ROUND(AVG(b.monthly_charges), 2)  AS avg_monthly_bill,
       ROUND(AVG(c.tenure_months), 1)    AS avg_tenure_months
FROM customers c
JOIN billing b ON c.customer_id = b.customer_id
GROUP BY c.churned;


-- name: 7. Highest-risk group: month-to-month + fiber + no tech support
SELECT CASE WHEN b.contract = 'Month-to-month'
             AND s.internet_service = 'Fiber optic'
             AND s.tech_support = 0
            THEN 'High-risk group' ELSE 'Everyone else' END AS segment,
       COUNT(*)                          AS customers,
       ROUND(AVG(c.churned) * 100, 1)    AS churn_rate_pct
FROM customers c
JOIN services s ON c.customer_id = s.customer_id
JOIN billing  b ON c.customer_id = b.customer_id
GROUP BY segment
ORDER BY churn_rate_pct DESC;


-- name: 8. Monthly revenue lost to churn
SELECT ROUND(SUM(CASE WHEN c.churned = 1 THEN b.monthly_charges ELSE 0 END), 0) AS monthly_revenue_lost,
       ROUND(SUM(b.monthly_charges), 0)                                          AS total_monthly_revenue,
       ROUND(SUM(CASE WHEN c.churned = 1 THEN b.monthly_charges ELSE 0 END)
             * 100.0 / SUM(b.monthly_charges), 1)                                AS pct_revenue_lost
FROM customers c
JOIN billing b ON c.customer_id = b.customer_id;
