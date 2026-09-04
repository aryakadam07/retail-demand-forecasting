{{ config(materialized='table') }}

select * from {{ ref('int_weekly_sales') }}
