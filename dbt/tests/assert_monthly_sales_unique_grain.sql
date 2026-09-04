-- Asserts that int_monthly_sales has no duplicate records at its grain (year + month + store_id + item_id)
select
    year,
    month,
    store_id,
    item_id,
    count(*) as record_count
from {{ ref('int_monthly_sales') }}
group by year, month, store_id, item_id
having count(*) > 1
