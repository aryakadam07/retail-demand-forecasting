"""
Retail Demand Forecasting — Data Warehouse Client
Abstracts Google BigQuery and DuckDB storage backends.
"""

import os
import sqlite3
import pandas as pd
from typing import Optional, Union
from src import config

try:
    from google.cloud import bigquery
    from google.api_core.exceptions import GoogleAPIError
    BQ_AVAILABLE = True
except ImportError:
    BQ_AVAILABLE = False

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False


class WarehouseClient:
    """Unified Data Warehouse Client supporting BigQuery, DuckDB, and SQLite backends."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        if use_local_duckdb is None:
            self.use_local_duckdb = config.USE_LOCAL_DUCKDB
        else:
            self.use_local_duckdb = use_local_duckdb

        self.project_id = config.GCP_PROJECT_ID
        self.dataset_id = config.BIGQUERY_DATASET
        self.duckdb_path = str(config.LOCAL_DUCKDB_PATH)
        self.sqlite_path = str(config.DATA_DIR / "m5_warehouse.db")

        if not self.use_local_duckdb:
            if not BQ_AVAILABLE or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                self.use_local_duckdb = True

        self.engine_mode = "duckdb" if DUCKDB_AVAILABLE else "sqlite"
        if not self.use_local_duckdb and BQ_AVAILABLE:
            self.engine_mode = "bigquery"

    def create_dataset(self) -> None:
        """Ensures target dataset or database exists."""
        if self.engine_mode == "bigquery":
            client = bigquery.Client(project=self.project_id)
            dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
            try:
                client.get_dataset(dataset_ref)
            except Exception:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                client.create_dataset(dataset, timeout=30)
        elif self.engine_mode == "duckdb":
            conn = duckdb.connect(self.duckdb_path)
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.dataset_id};")
            conn.close()
        else:  # sqlite fallback
            conn = sqlite3.connect(self.sqlite_path)
            conn.close()

    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "replace"
    ) -> bool:
        """Uploads a pandas DataFrame into the warehouse table."""
        full_table = f"{self.dataset_id}_{table_name}" if self.engine_mode == "sqlite" else f"{self.dataset_id}.{table_name}"
        
        if self.engine_mode == "bigquery":
            client = bigquery.Client(project=self.project_id)
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            write_disposition = (
                bigquery.WriteDisposition.WRITE_TRUNCATE
                if if_exists == "replace"
                else bigquery.WriteDisposition.WRITE_APPEND
            )
            job_config = bigquery.LoadJobConfig(write_disposition=write_disposition)
            job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()
            print(f"[BigQuery] Loaded {len(df):,} rows into '{table_ref}'")
            return True
        elif self.engine_mode == "duckdb":
            conn = duckdb.connect(self.duckdb_path)
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.dataset_id};")
            if if_exists == "replace":
                conn.execute(f"DROP TABLE IF EXISTS {full_table};")
                conn.execute(f"CREATE TABLE {full_table} AS SELECT * FROM df;")
            elif if_exists == "append":
                conn.execute(f"INSERT INTO {full_table} SELECT * FROM df;")
            conn.close()
            print(f"[DuckDB] Loaded {len(df):,} rows into '{full_table}'")
            return True
        else:  # sqlite
            conn = sqlite3.connect(self.sqlite_path)
            df.to_sql(full_table, conn, if_exists=if_exists, index=False)
            conn.close()
            print(f"[SQLite] Loaded {len(df):,} rows into '{full_table}'")
            return True

    def query(self, sql_query: str) -> pd.DataFrame:
        """Executes a SQL query and returns results as a Pandas DataFrame."""
        if self.engine_mode == "bigquery":
            client = bigquery.Client(project=self.project_id)
            query_job = client.query(sql_query)
            return query_job.to_dataframe()
        elif self.engine_mode == "duckdb":
            conn = duckdb.connect(self.duckdb_path)
            result_df = conn.execute(sql_query).df()
            conn.close()
            return result_df
        else:  # sqlite
            # Adapt schema prefix queries (dataset.table -> dataset_table)
            sqlite_query = sql_query.replace(f"{self.dataset_id}.", f"{self.dataset_id}_")
            conn = sqlite3.connect(self.sqlite_path)
            result_df = pd.read_sql_query(sqlite_query, conn)
            conn.close()
            return result_df

    def verify_table(self, table_name: str, sample_limit: int = 5) -> dict:
        """
        Verifies table existence, counts total rows, lists column names, and fetches sample records.
        """
        full_table = f"{self.dataset_id}.{table_name}"
        try:
            count_df = self.query(f"SELECT COUNT(*) AS row_count FROM {full_table}")
            row_count = int(count_df.iloc[0]["row_count"])

            sample_df = self.query(f"SELECT * FROM {full_table} LIMIT {sample_limit}")
            columns = list(sample_df.columns)

            return {
                "exists": True,
                "table_name": table_name,
                "full_table": full_table,
                "row_count": row_count,
                "columns": columns,
                "sample_head": sample_df.to_dict(orient="records"),
            }
        except Exception as exc:
            return {
                "exists": False,
                "table_name": table_name,
                "full_table": full_table,
                "error": str(exc),
            }


if __name__ == "__main__":
    client = WarehouseClient()
    client.create_dataset()
    test_df = pd.DataFrame({"id": [1, 2, 3], "val": ["A", "B", "C"]})
    client.load_dataframe(test_df, "test_table")
    df_out = client.query(f"SELECT * FROM {client.dataset_id}.test_table")
    print("Verification Query Output:\n", df_out)
    print("Verify Table Result:\n", client.verify_table("test_table"))

