{{ config(materialized='view') }}

with raw_prices as (
    select * from {{ source('retail_m5_dw', 'clean_sell_prices') }}
)

select
    cast(store_id as string) as store_id,
    cast(item_id as string) as item_id,
    cast(wm_yr_wk as bigint) as wm_yr_wk,
    cast(sell_price as double) as sell_price
from raw_prices
