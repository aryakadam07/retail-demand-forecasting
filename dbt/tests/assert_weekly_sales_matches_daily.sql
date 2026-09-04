-- Asserts that total weekly sales matches total daily sales across the entire dataset
with daily_total as (
    select sum(sales) as total_daily from {{ ref('int_daily_sales') }}
),
weekly_total as (
    select sum(total_weekly_sales) as total_weekly from {{ ref('int_weekly_sales') }}
)
select
    daily_total.total_daily,
    weekly_total.total_weekly
from daily_total, weekly_total
where daily_total.total_daily != weekly_total.total_weekly
