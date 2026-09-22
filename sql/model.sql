-- SQLite dialect. Raw tables are loaded and validated by run_project.py.
-- Grain: exactly ONE row per order. Aggregate child tables BEFORE joining.
CREATE TABLE order_fact AS
WITH item_totals AS (
 SELECT order_id, COUNT(*) AS item_count,
        SUM(price_cents) AS item_sales_cents,
        SUM(freight_cents) AS freight_cents,
        COUNT(DISTINCT seller_id) AS seller_count,
        MIN(seller_id) AS sole_seller_id
 FROM items GROUP BY order_id
), review_totals AS (
 -- One order gets one mean score even if it has multiple review records.
 SELECT order_id, AVG(CAST(review_score AS REAL)) AS review_score,
        COUNT(*) AS review_records
 FROM reviews GROUP BY order_id
), base AS (
 SELECT o.*, c.customer_unique_id, c.customer_state,
        substr(o.order_purchase_timestamp,1,4) AS purchase_year,
        substr(o.order_purchase_timestamp,1,7) AS purchase_month,
        i.item_count, i.item_sales_cents, i.freight_cents,
        i.seller_count, i.sole_seller_id, r.review_score, r.review_records,
        CASE WHEN o.order_status='delivered'
          AND julianday(o.order_delivered_customer_date) IS NOT NULL
          AND julianday(o.order_estimated_delivery_date) IS NOT NULL
          AND julianday(o.order_purchase_timestamp) IS NOT NULL
          AND julianday(o.order_delivered_customer_date)>=julianday(o.order_purchase_timestamp)
          AND date(o.order_estimated_delivery_date)>=date(o.order_purchase_timestamp)
          THEN 1 ELSE 0 END AS eligible_delivery
 FROM orders o LEFT JOIN customers c USING(customer_id)
 LEFT JOIN item_totals i USING(order_id)
 LEFT JOIN review_totals r USING(order_id)
)
SELECT *,
 CASE WHEN eligible_delivery=1 THEN
   CASE WHEN date(order_delivered_customer_date)>date(order_estimated_delivery_date)
        THEN 1 ELSE 0 END END AS is_late,
 CASE WHEN eligible_delivery=1 THEN
   julianday(order_delivered_customer_date)-julianday(order_purchase_timestamp)
 END AS delivery_days
FROM base;
CREATE UNIQUE INDEX fact_order_id ON order_fact(order_id);
CREATE INDEX fact_year_state ON order_fact(purchase_year, customer_state);

-- Seller grain: one row per single-seller order. Delivery timestamps belong
-- to the whole order, so multi-seller orders are excluded from seller ranking.
CREATE TABLE seller_fact AS
SELECT f.*, s.seller_city, s.seller_state
FROM order_fact f JOIN sellers s ON s.seller_id=f.sole_seller_id
WHERE f.seller_count=1;

-- Category grain: one row per order/category. Item sales remain additive,
-- but order counts across categories are NOT additive.
CREATE TABLE category_fact AS
WITH category_items AS (
 SELECT i.order_id,
        COALESCE(t.product_category_name_english,p.product_category_name,'Unknown') AS category,
        SUM(i.price_cents) AS category_sales_cents
 FROM items i JOIN products p USING(product_id)
 LEFT JOIN category_translation t USING(product_category_name)
 GROUP BY i.order_id, category
)
SELECT f.order_id,f.purchase_year,f.purchase_month,f.customer_state,
       f.order_status,f.eligible_delivery,f.is_late,f.delivery_days,f.review_score,
       c.category,c.category_sales_cents
FROM category_items c JOIN order_fact f USING(order_id);
