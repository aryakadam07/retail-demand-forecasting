# Retail Demand Forecasting & Inventory Optimization System

An end-to-end production-oriented analytics and forecasting engine built on Walmart's **M5 Forecasting Dataset**.

## Project Architecture

```
retail-demand-forecasting/
├── data/
│   ├── README.md
│   └── processed/
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   └── dbt_project.yml
├── src/
│   ├── config.py
│   ├── data_ingestion/
│   │   ├── bq_client.py
│   │   └── m5_loader.py
│   ├── preprocessing/
│   │   └── clean_and_melt.py
│   ├── features/
│   ├── forecasting/
│   └── inventory/
├── models/
├── dashboard/
├── notebooks/
│   └── 01_exploratory_data_analysis.py
├── tests/
│   └── test_phase1.py
├── docs/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Development Phases

- [x] **Phase 1 — Data Architecture & ETL**: Setup, BigQuery/DuckDB Data Warehouse ingestion, wide-to-long sales melting, data quality checks, and EDA.
- [ ] **Phase 2 — dbt Data Modeling**: Staging, intermediate transformations, fact & dimension tables, data lineage, and tests.
- [ ] **Phase 3 — Demand Forecasting**: Time-series feature engineering, baseline models, Prophet, LightGBM, model evaluation (MAE/RMSE/MAPE), and selection.
- [ ] **Phase 4 — Inventory Optimization & Dashboard**: Safety stock calculation, reorder point, interactive Streamlit dashboard, and what-if price scenario simulator.

---

## Quick Start & Reproducible Setup

### 1. Environment Setup
```bash
# Navigate to the project directory
cd C:\Users\HP\Desktop\retail-demand-forecasting

# Create and activate a Python virtual environment
python -m venv venv
venv\Scripts\activate

# Install project dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your credentials:
```bash
copy .env.example .env
```
To run offline locally without GCP credentials, set `USE_LOCAL_DUCKDB=True` in `.env`.

---

## Phase 1 Execution Commands

### Step 1: Run Ingestion (Load Raw M5 Data to Warehouse)
```bash
python -m src.data_ingestion.m5_loader
```

### Step 2: Run Data Preprocessing (Unpivot & Clean Sales)
```bash
python -m src.preprocessing.clean_and_melt
```

### Step 3: Run Exploratory Data Analysis Report
```bash
python -m notebooks.01_exploratory_data_analysis
```

### Step 4: Run Automated Tests
```bash
pytest tests/test_phase1.py -v
```
