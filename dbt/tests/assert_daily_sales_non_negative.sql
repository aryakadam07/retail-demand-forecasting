-- Asserts that daily sales volume is non-negative
select
    sales_date,
    store_id,
    item_id,
    sales
from {{ ref('int_daily_sales') }}
where sales < 0
