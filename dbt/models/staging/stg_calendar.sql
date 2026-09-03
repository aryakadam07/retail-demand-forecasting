{{ config(materialized='view') }}

with raw_calendar as (
    select * from {{ source('retail_m5_dw', 'clean_calendar') }}
)

select
    cast(date as date) as sales_date,
    cast(wm_yr_wk as bigint) as wm_yr_wk,
    cast(weekday as string) as weekday,
    cast(wday as integer) as day_of_week,
    cast(month as integer) as month,
    cast(year as integer) as year,
    cast(d as string) as day_id,
    cast(event_name_1 as string) as event_name_1,
    cast(event_type_1 as string) as event_type_1,
    cast(event_name_2 as string) as event_name_2,
    cast(event_type_2 as string) as event_type_2,
    cast(snap_CA as integer) as snap_ca,
    cast(snap_TX as integer) as snap_tx,
    cast(snap_WI as integer) as snap_wi
from raw_calendar
