-- =====================================================================
-- 02_data_cleaning.sql
-- Builds CLEAN copies of each raw table (raw tables are never changed).
-- =====================================================================

DROP TABLE IF EXISTS clean_products;
DROP TABLE IF EXISTS clean_warehouses;
DROP TABLE IF EXISTS clean_sales;
DROP TABLE IF EXISTS clean_inventory;
DROP TABLE IF EXISTS clean_forecast;

-- ---------------------------------------------------------------------
-- 1. PRODUCTS: fix category spelling, remove duplicate, fill missing cost
-- ---------------------------------------------------------------------
CREATE TABLE clean_products AS
WITH std AS (
    SELECT
        product_id,
        product_name,
        CASE LOWER(TRIM(category))
            WHEN 'electronics'     THEN 'Electronics'
            WHEN 'home & kitchen'  THEN 'Home & Kitchen'
            WHEN 'apparel'         THEN 'Apparel'
            WHEN 'grocery'         THEN 'Grocery'
            WHEN 'health & beauty' THEN 'Health & Beauty'
            WHEN 'office supplies' THEN 'Office Supplies'
        END AS category,
        unit_cost, unit_price, shelf_life_days, lead_time_days,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY rowid) AS rn
    FROM products
),
dedup AS (SELECT * FROM std WHERE rn = 1),
cat_avg AS (
    SELECT category, AVG(unit_cost) AS avg_cost
    FROM dedup WHERE unit_cost IS NOT NULL GROUP BY category
)
SELECT
    d.product_id,
    d.product_name,
    d.category,
    ROUND(COALESCE(d.unit_cost, c.avg_cost), 2) AS unit_cost,
    d.unit_price,
    d.shelf_life_days,
    d.lead_time_days
FROM dedup d
LEFT JOIN cat_avg c ON c.category = d.category;

-- Business-rule fix: Sunscreen was wrongly filed under Grocery in the raw data
UPDATE clean_products SET category = 'Health & Beauty' WHERE product_name = 'Sunscreen';

-- ---------------------------------------------------------------------
-- 2. WAREHOUSES: already clean, copy as is
-- ---------------------------------------------------------------------
CREATE TABLE clean_warehouses AS SELECT * FROM warehouses;

-- ---------------------------------------------------------------------
-- 3. SALES
-- ---------------------------------------------------------------------
CREATE TABLE clean_sales AS
WITH std AS (
    SELECT
        sale_id,
        order_date,
        UPPER(TRIM(product_id)) AS product_id,
        warehouse_id,
        ABS(quantity)           AS quantity,
        unit_price,
        ROW_NUMBER() OVER (PARTITION BY sale_id ORDER BY rowid) AS rn
    FROM sales
)
SELECT sale_id, order_date, product_id, warehouse_id, quantity, unit_price
FROM std
WHERE rn = 1
  AND quantity     IS NOT NULL
  AND warehouse_id IS NOT NULL
  AND quantity <= 1000;

-- ---------------------------------------------------------------------
-- 4. INVENTORY
-- ---------------------------------------------------------------------
CREATE TABLE clean_inventory AS
WITH std AS (
    SELECT
        snapshot_date, product_id, warehouse_id,
        ABS(units_on_hand) AS units_on_hand,
        last_received_date,
        ROW_NUMBER() OVER (
            PARTITION BY snapshot_date, product_id, warehouse_id ORDER BY rowid
        ) AS rn
    FROM inventory
)
SELECT snapshot_date, product_id, warehouse_id, units_on_hand, last_received_date
FROM std WHERE rn = 1;

-- ---------------------------------------------------------------------
-- 5. FORECAST
-- ---------------------------------------------------------------------
CREATE TABLE clean_forecast AS
WITH std AS (
    SELECT
        forecast_month, product_id, warehouse_id, forecast_qty, actual_qty,
        ROW_NUMBER() OVER (
            PARTITION BY forecast_month, product_id, warehouse_id ORDER BY rowid
        ) AS rn
    FROM forecast
)
SELECT forecast_month, product_id, warehouse_id, forecast_qty, actual_qty
FROM std
WHERE rn = 1 AND forecast_qty IS NOT NULL;