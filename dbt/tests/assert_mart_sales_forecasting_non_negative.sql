-- Asserts that sales and sell_price are non-negative in mart_sales_forecasting
select
    date,
    store_id,
    item_id,
    sales,
    sell_price
from {{ ref('mart_sales_forecasting') }}
where sales < 0 or (sell_price is not null and sell_price < 0)
