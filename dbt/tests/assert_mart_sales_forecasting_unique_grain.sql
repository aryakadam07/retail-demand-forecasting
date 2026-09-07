-- Asserts that mart_sales_forecasting has no duplicate records at its grain (item_id + store_id + date)
select
    date,
    store_id,
    item_id,
    count(*) as record_count
from {{ ref('mart_sales_forecasting') }}
group by date, store_id, item_id
having count(*) > 1
