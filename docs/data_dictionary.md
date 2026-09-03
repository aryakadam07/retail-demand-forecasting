# Retail Demand Forecasting — Data Dictionary

This document details the schema, column definitions, data types, nullability rules, and domain constraints for all tables in the `retail_m5_dw` Data Warehouse created during **Week 1 (Data Architecture & ETL)**.

---

## Table Overview

| Table Name | Layer | Description | Target Engine |
| :--- | :--- | :--- | :--- |
| `raw_calendar` | Raw Ingestion | Raw M5 calendar metadata with event annotations | BigQuery / Local |
| `raw_sales_train_validation` | Raw Ingestion | Raw M5 daily sales volumes across wide columns (`d_1`...`d_N`) | BigQuery / Local |
| `raw_sell_prices` | Raw Ingestion | Raw M5 weekly unit sell prices by store and item | BigQuery / Local |
| `clean_calendar` | Data Quality | Standardized ISO dates (`YYYY-MM-DD`), verified event categories | BigQuery / Local |
| `clean_sales_train_validation` | Data Quality | Cleaned wide sales table with non-negative sales volume constraints | BigQuery / Local |
| `clean_sell_prices` | Data Quality | Cleaned unit price table with numeric float enforcement | BigQuery / Local |
| `fact_daily_sales` (alias: `stg_sales_long`) | Analytical Fact Layer | Standardized unpivoted long daily sales table with joined dates & sell prices | BigQuery / Local |

---

## Analytical Table Schema (`fact_daily_sales`)

Target Table Name: `retail_m5_dw.fact_daily_sales`  
Primary Key: `(date, item_id, store_id)`

| Column Name | Data Type | Nullable | Primary Key | Foreign Key / Mapping | Description & Domain Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date` | `DATE` / `STRING` | No | Yes | `clean_calendar.date` | ISO-8601 calendar date (`YYYY-MM-DD`). Bounds: `2011-01-29` to `2016-06-19`. |
| `item_id` | `STRING` | No | Yes | `clean_sales.item_id` | Product stock keeping unit identifier (e.g. `HOBBIES_1_001`, `FOODS_1_002`). |
| `dept_id` | `STRING` | No | No | `clean_sales.dept_id` | Product department identifier (e.g. `HOBBIES_1`, `FOODS_1`, `HOUSEHOLD_2`). |
| `cat_id` | `STRING` | No | No | `clean_sales.cat_id` | High-level product category (`FOODS`, `HOBBIES`, `HOUSEHOLD`). |
| `store_id` | `STRING` | No | Yes | `clean_sales.store_id` | Retail store location identifier (e.g. `CA_1`, `CA_2`, `TX_1`, `WI_1`). |
| `state_id` | `STRING` | No | No | `clean_sales.state_id` | US state abbreviation where store is located (`CA`, `TX`, `WI`). |
| `sales` | `INTEGER` / `NUMERIC` | No | No | — | Daily unit sales volume. Non-negative constraint ($sales \ge 0$). |
| `sell_price` | `FLOAT` / `NUMERIC` | Yes | No | `clean_sell_prices.sell_price` | Unit selling price in USD ($). Nullable for weeks prior to product release in store. |

---

## Data Quality & Clean Tables Schema

### 1. `clean_calendar`
Target Table Name: `retail_m5_dw.clean_calendar`

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `date` | `DATE` / `STRING` | No | ISO calendar date formatted as `YYYY-MM-DD`. |
| `wm_yr_wk` | `INTEGER` | No | Walmart weekly temporal identifier (e.g., `11101`). |
| `weekday` | `STRING` | No | Day of week name (`Monday` ... `Sunday`). |
| `wday` | `INTEGER` | No | Numerical day of week identifier (`1` = Saturday ... `7` = Friday). |
| `month` | `INTEGER` | No | Calendar month index (`1` to `12`). |
| `year` | `INTEGER` | No | Calendar year (`2011` to `2016`). |
| `d` | `STRING` | No | Day column key mapping (`d_1` to `d_1969`). |
| `event_name_1` | `STRING` | Yes | Name of holiday or special event occurrence 1. |
| `event_type_1` | `STRING` | Yes | Domain classification of event 1 (`Sporting`, `Cultural`, `National`, `Religious`). |
| `event_name_2` | `STRING` | Yes | Name of holiday or special event occurrence 2. |
| `event_type_2` | `STRING` | Yes | Domain classification of event 2. |
| `snap_CA` | `INTEGER` | No | Binary flag (`0`/`1`) indicating SNAP food stamp entitlement day in California. |
| `snap_TX` | `INTEGER` | No | Binary flag (`0`/`1`) indicating SNAP food stamp entitlement day in Texas. |
| `snap_WI` | `INTEGER` | No | Binary flag (`0`/`1`) indicating SNAP food stamp entitlement day in Wisconsin. |

---

### 2. `clean_sales_train_validation`
Target Table Name: `retail_m5_dw.clean_sales_train_validation`

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | `STRING` | No | Composite series key (`item_id` + `store_id` + `validation`). |
| `item_id` | `STRING` | No | Product SKU identifier. |
| `dept_id` | `STRING` | No | Department identifier. |
| `cat_id` | `STRING` | No | Category identifier. |
| `store_id` | `STRING` | No | Store location identifier. |
| `state_id` | `STRING` | No | State identifier (`CA`, `TX`, `WI`). |
| `d_1` ... `d_N` | `INTEGER` | No | Daily sales volume on day $1 \dots N$. Non-negative numeric integer. |

---

### 3. `clean_sell_prices`
Target Table Name: `retail_m5_dw.clean_sell_prices`

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `store_id` | `STRING` | No | Store location identifier. |
| `item_id` | `STRING` | No | Product SKU identifier. |
| `wm_yr_wk` | `INTEGER` | No | Walmart weekly temporal identifier. |
| `sell_price` | `FLOAT` | No | Regular unit selling price ($). |

---

## Dimension Hierarchy Mapping Rules

1. **Item Hierarchy**: Each `item_id` maps to exactly 1 `dept_id` and 1 `cat_id`.
   - `HOBBIES_1_001` $\rightarrow$ `HOBBIES_1` $\rightarrow$ `HOBBIES`
   - `FOODS_1_002` $\rightarrow$ `FOODS_1` $\rightarrow$ `FOODS`
2. **Store Hierarchy**: Each `store_id` maps to exactly 1 `state_id`.
   - `CA_1`, `CA_2` $\rightarrow$ `CA`
   - `TX_1` $\rightarrow$ `TX`
   - `WI_1` $\rightarrow$ `WI`
