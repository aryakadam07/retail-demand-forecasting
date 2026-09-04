-- Asserts that total monthly sales matches total daily sales across the entire dataset
with daily_total as (
    select sum(sales) as total_daily from {{ ref('int_daily_sales') }}
),
monthly_total as (
    select sum(total_monthly_sales) as total_monthly from {{ ref('int_monthly_sales') }}
)
select
    daily_total.total_daily,
    monthly_total.total_monthly
from daily_total, monthly_total
where daily_total.total_daily != monthly_total.total_monthly
