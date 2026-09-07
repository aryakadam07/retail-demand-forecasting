{{ config(materialized='table') }}

/*
    Mart: mart_sales_forecasting
    Description: Final analytical table prepared for demand forecasting models (Prophet & LightGBM).
    Grain: One record per item_id + store_id + date combination.
    Hierarchy: State -> Store -> Category -> Department -> Item
*/

with daily_sales as (
    select * from {{ ref('int_daily_sales') }}
)

select
    sales_date as date,
    sales_date,
    item_id,
    store_id,
    state_id,
    cat_id as category,
    cat_id,
    dept_id as department,
    dept_id,
    sales,
    sell_price,
    wm_yr_wk,
    year,
    month,
    weekday,
    day_of_week,
    day_id,
    event_name_1,
    event_type_1,
    event_name_2,
    event_type_2,
    snap_ca,
    snap_tx,
    snap_wi
from daily_sales
