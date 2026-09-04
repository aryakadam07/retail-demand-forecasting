-- Asserts that int_weekly_sales has no duplicate records at its grain (wm_yr_wk + store_id + item_id)
select
    wm_yr_wk,
    store_id,
    item_id,
    count(*) as record_count
from {{ ref('int_weekly_sales') }}
group by wm_yr_wk, store_id, item_id
having count(*) > 1
