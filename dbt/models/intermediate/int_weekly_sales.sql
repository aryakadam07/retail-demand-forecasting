{{ config(materialized='view') }}

with daily_sales as (
    select * from {{ ref('int_daily_sales') }}
)

select
    wm_yr_wk,
    year,
    state_id,
    store_id,
    cat_id,
    dept_id,
    item_id,
    min(sales_date) as week_start_date,
    max(sales_date) as week_end_date,
    sum(sales) as total_weekly_sales,
    round(avg(sell_price), 4) as avg_sell_price,
    min(sell_price) as min_sell_price,
    max(sell_price) as max_sell_price,
    count(distinct case when sales > 0 then sales_date end) as selling_days,
    count(distinct sales_date) as recorded_days
from daily_sales
group by
    wm_yr_wk,
    year,
    state_id,
    store_id,
    cat_id,
    dept_id,
    item_id
