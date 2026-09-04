{{ config(materialized='view') }}

with sales_fact as (
    select
        cast(date as date) as sales_date,
        cast(item_id as string) as item_id,
        cast(dept_id as string) as dept_id,
        cast(cat_id as string) as cat_id,
        cast(store_id as string) as store_id,
        cast(state_id as string) as state_id,
        cast(sales as bigint) as sales,
        cast(sell_price as double) as sell_price
    from {{ source('retail_m5_dw', 'fact_daily_sales') }}
),

calendar as (
    select * from {{ ref('stg_calendar') }}
)

select
    f.sales_date,
    f.state_id,
    f.store_id,
    f.cat_id,
    f.dept_id,
    f.item_id,
    f.sales,
    f.sell_price,
    c.wm_yr_wk,
    c.year,
    c.month,
    c.weekday,
    c.day_of_week,
    c.day_id,
    c.event_name_1,
    c.event_type_1,
    c.event_name_2,
    c.event_type_2,
    c.snap_ca,
    c.snap_tx,
    c.snap_wi
from sales_fact f
left join calendar c
    on f.sales_date = c.sales_date
