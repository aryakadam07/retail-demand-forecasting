-- Asserts that int_daily_sales has no duplicate records at its grain (sales_date + store_id + item_id)
select
    sales_date,
    store_id,
    item_id,
    count(*) as record_count
from {{ ref('int_daily_sales') }}
group by sales_date, store_id, item_id
having count(*) > 1
