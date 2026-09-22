-- Open build/olist.sqlite in DBeaver using a SQLite connection.
-- Run individual SELECT statements. This file does not modify the database.

-- 1. What statuses exist? Grain: order.
SELECT order_status, COUNT(*) AS orders FROM order_fact
GROUP BY order_status ORDER BY orders DESC;

-- 2. Headline metrics. Merchandise sales exclude freight and non-delivered orders.
SELECT COUNT(*) AS all_orders,
 SUM(order_status='delivered') AS delivered_orders,
 SUM(CASE WHEN order_status='delivered' THEN item_sales_cents END)/100.0 AS delivered_item_sales_brl,
 SUM(CASE WHEN order_status='delivered' THEN item_sales_cents END)/100.0 /
 NULLIF(SUM(order_status='delivered' AND item_sales_cents IS NOT NULL),0) AS item_aov_brl,
 SUM(eligible_delivery) AS eligible_orders,
 SUM(is_late) AS late_orders,
 100.0*SUM(is_late)/NULLIF(SUM(eligible_delivery),0) AS late_pct,
 AVG(delivery_days) AS avg_delivery_days
FROM order_fact;

-- 3. Purchase-month trend. Do not interpret sparse boundary months as growth.
SELECT purchase_month,COUNT(*) AS all_orders,
 SUM(CASE WHEN order_status='delivered' THEN item_sales_cents END)/100.0 AS sales_brl,
 100.0*SUM(is_late)/NULLIF(SUM(eligible_delivery),0) AS late_pct
FROM order_fact GROUP BY purchase_month ORDER BY purchase_month;

-- 4. States with enough observations; prioritize volume alongside rate.
SELECT customer_state,SUM(eligible_delivery) AS eligible_orders,
 SUM(is_late) AS late_orders,
 100.0*SUM(is_late)/SUM(eligible_delivery) AS late_pct
FROM order_fact GROUP BY customer_state HAVING SUM(eligible_delivery)>=100
ORDER BY late_orders DESC;

-- 5. Seller investigation queue: single-seller orders only.
SELECT sole_seller_id,seller_city,seller_state,
 SUM(eligible_delivery) AS eligible_orders,SUM(is_late) AS late_orders,
 100.0*SUM(is_late)/SUM(eligible_delivery) AS late_pct
FROM seller_fact GROUP BY sole_seller_id,seller_city,seller_state
HAVING SUM(eligible_delivery)>=100 ORDER BY late_orders DESC LIMIT 15;

-- 6. Category comparisons. Do not sum these order counts across categories.
SELECT category,SUM(eligible_delivery) AS eligible_orders,
 SUM(is_late) AS late_orders,
 100.0*SUM(is_late)/SUM(eligible_delivery) AS late_pct,
 SUM(CASE WHEN order_status='delivered' THEN category_sales_cents END)/100.0 AS sales_brl
FROM category_fact GROUP BY category HAVING SUM(eligible_delivery)>=100
ORDER BY late_orders DESC LIMIT 15;

-- 7. Association between delivery and reviews. This is NOT a causal estimate.
SELECT CASE WHEN is_late=1 THEN 'Late' ELSE 'On time' END AS delivery_group,
 COUNT(*) AS eligible_orders,COUNT(review_score) AS reviewed_orders,
 AVG(review_score) AS mean_order_review
FROM order_fact WHERE eligible_delivery=1 GROUP BY is_late;

-- 8. Validate join grain. Both numbers must equal source order count.
SELECT COUNT(*) AS rows,COUNT(DISTINCT order_id) AS distinct_orders FROM order_fact;

-- 9. Window function: rank sellers within each seller state.
WITH seller_metrics AS (
 SELECT sole_seller_id,seller_state,SUM(is_late) AS late_orders,
 SUM(eligible_delivery) AS eligible_orders
 FROM seller_fact GROUP BY sole_seller_id,seller_state
 HAVING SUM(eligible_delivery)>=100
)
SELECT *, DENSE_RANK() OVER(PARTITION BY seller_state ORDER BY late_orders DESC) AS state_rank
FROM seller_metrics ORDER BY seller_state,state_rank;

-- 10. Cancellation rate has ALL orders as its denominator.
SELECT 100.0*SUM(order_status='canceled')/COUNT(*) AS cancellation_pct FROM order_fact;
