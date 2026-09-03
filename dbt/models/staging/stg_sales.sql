{{ config(materialized='view') }}

with raw_sales as (
    select * from {{ source('retail_m5_dw', 'clean_sales_train_validation') }}
)

select
    cast(id as string) as series_id,
    cast(item_id as string) as item_id,
    cast(dept_id as string) as dept_id,
    cast(cat_id as string) as cat_id,
    cast(store_id as string) as store_id,
    cast(state_id as string) as state_id
from raw_sales
