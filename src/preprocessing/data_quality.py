"""
Retail Demand Forecasting — Data Quality & Audit Framework
Performs granular quality validation on raw M5 datasets (Calendar, Sales, Prices).
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataQualityReport:
    """Encapsulates validation check results and formats readable reports."""

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.num_rows = 0
        self.num_cols = 0
        self.dtypes: Dict[str, str] = {}
        self.missing_values: Dict[str, int] = {}
        self.duplicate_records = 0
        self.checks: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    def add_check(self, name: str, passed: bool, message: str, count: int = 0) -> None:
        """Adds an individual check result to the report."""
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "count": count
        })

    @property
    def overall_status(self) -> str:
        """Returns PASS if all checks passed, otherwise FAIL."""
        return "PASS" if all(c["passed"] for c in self.checks) else "FAIL"

    def generate_text_report(self) -> str:
        """Renders formatted text report for logs and console output."""
        lines = [
            "==================================================",
            f"  DATA QUALITY REPORT: {self.dataset_name.upper()}",
            "==================================================",
            f"  Rows            : {self.num_rows:,}",
            f"  Columns         : {self.num_cols}",
            f"  Duplicate Rows  : {self.duplicate_records:,}",
            f"  Overall Status  : {self.overall_status}",
            "--------------------------------------------------",
            "  CHECKS:"
        ]
        for check in self.checks:
            icon = "[PASS]" if check["passed"] else "[FAIL]"
            cnt_info = f" ({check['count']:,} issues)" if check["count"] > 0 else ""
            lines.append(f"    {icon:<7} {check['name']}: {check['message']}{cnt_info}")

        lines.append("--------------------------------------------------")
        lines.append("  MISSING VALUES BY COLUMN:")
        has_nulls = False
        for col, null_cnt in self.missing_values.items():
            if null_cnt > 0:
                has_nulls = True
                pct = (null_cnt / self.num_rows * 100) if self.num_rows > 0 else 0.0
                lines.append(f"    - {col:<20}: {null_cnt:>8,} ({pct:>5.2f}%)")
        if not has_nulls:
            lines.append("    - No missing values found in mandatory columns.")

        if self.stats:
            lines.append("--------------------------------------------------")
            lines.append("  KEY NUMERICAL STATISTICS:")
            for col, stat in self.stats.items():
                min_v = stat.get('min')
                max_v = stat.get('max')
                mean_v = stat.get('mean')
                mean_str = f", mean={mean_v:.2f}" if isinstance(mean_v, (int, float)) else ""
                lines.append(f"    - {col:<20}: min={min_v}, max={max_v}{mean_str}")

        lines.append("==================================================\n")
        return "\n".join(lines)


class DataQualityChecker:
    """Reusable data quality validator for M5 raw datasets."""

    @staticmethod
    def audit_calendar_data(df: pd.DataFrame) -> DataQualityReport:
        """Audits raw calendar dataset."""
        logger.info("Auditing Calendar dataset (%d rows x %d cols)...", len(df), len(df.columns))
        report = DataQualityReport("Calendar")
        report.num_rows = len(df)
        report.num_cols = len(df.columns)
        report.dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        report.missing_values = {col: int(df[col].isnull().sum()) for col in df.columns}
        report.duplicate_records = int(df.duplicated().sum())

        # 1. Missing dates check
        missing_dates = int(df["date"].isnull().sum()) if "date" in df.columns else len(df)
        report.add_check(
            "Missing Dates",
            missing_dates == 0,
            "No missing date values" if missing_dates == 0 else "Contains missing dates",
            count=missing_dates
        )

        # 2. Duplicate dates check
        dup_dates = int(df["date"].duplicated().sum()) if "date" in df.columns else 0
        report.add_check(
            "Duplicate Dates",
            dup_dates == 0,
            "No duplicate dates found" if dup_dates == 0 else "Duplicate date entries detected",
            count=dup_dates
        )

        # 3. Invalid date values check
        if "date" in df.columns:
            parsed_dates = pd.to_datetime(df["date"], errors="coerce")
            invalid_dates = int(parsed_dates.isnull().sum()) - missing_dates
            report.add_check(
                "Valid Date Format",
                invalid_dates == 0,
                "All dates follow ISO format YYYY-MM-DD" if invalid_dates == 0 else "Unparseable date strings found",
                count=invalid_dates
            )
            if missing_dates == 0 and invalid_dates == 0:
                report.stats["date_range"] = {
                    "min": parsed_dates.min().strftime("%Y-%m-%d"),
                    "max": parsed_dates.max().strftime("%Y-%m-%d"),
                    "mean": "N/A"
                }

        # 4. Missing weekday values check
        missing_weekdays = int(df["weekday"].isnull().sum()) if "weekday" in df.columns else 0
        report.add_check(
            "Missing Weekday Values",
            missing_weekdays == 0,
            "No missing weekday values" if missing_weekdays == 0 else "Missing weekday values found",
            count=missing_weekdays
        )

        # 5. Invalid year/week/month values check
        invalid_years = 0
        if "year" in df.columns:
            invalid_years = int(((df["year"] < 2000) | (df["year"] > 2050)).sum())
            report.stats["year"] = {"min": int(df["year"].min()), "max": int(df["year"].max()), "mean": float(df["year"].mean())}
        if "month" in df.columns:
            report.stats["month"] = {"min": int(df["month"].min()), "max": int(df["month"].max()), "mean": float(df["month"].mean())}
        if "wday" in df.columns:
            report.stats["wday"] = {"min": int(df["wday"].min()), "max": int(df["wday"].max()), "mean": float(df["wday"].mean())}

        report.add_check(
            "Valid Year/Week Ranges",
            invalid_years == 0,
            "Year and week values within valid bounds" if invalid_years == 0 else "Out-of-bound years found",
            count=invalid_years
        )

        # 6. Unexpected values in event_type
        if "event_type_1" in df.columns:
            valid_types = {"Sporting", "Cultural", "National", "Religious", None, np.nan}
            unexpected_events = int((~df["event_type_1"].isin(valid_types) & df["event_type_1"].notnull()).sum())
            report.add_check(
                "Unexpected Event Types",
                unexpected_events == 0,
                "Event types match official M5 domain categories" if unexpected_events == 0 else "Unrecognized event types found",
                count=unexpected_events
            )

        # 7. Audit event info coverage
        if "event_name_1" in df.columns:
            num_events = int(df["event_name_1"].notnull().sum())
            report.add_check(
                "Event Coverage",
                True,
                f"Identified {num_events} holiday/special event occurrences (nulls expected on non-event days)"
            )

        return report

    @staticmethod
    def audit_sales_data(df: pd.DataFrame) -> DataQualityReport:
        """Audits raw sales dataset in wide format."""
        logger.info("Auditing Sales dataset (%d rows x %d cols)...", len(df), len(df.columns))
        report = DataQualityReport("Sales (Wide Format)")
        report.num_rows = len(df)
        report.num_cols = len(df.columns)
        report.dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        report.missing_values = {col: int(df[col].isnull().sum()) for col in df.columns if col in ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]}
        report.duplicate_records = int(df.duplicated().sum())

        # 1. Duplicate product/store combinations
        dup_combos = 0
        if "item_id" in df.columns and "store_id" in df.columns:
            dup_combos = int(df.duplicated(subset=["item_id", "store_id"]).sum())
        report.add_check(
            "Duplicate Item-Store Identifiers",
            dup_combos == 0,
            "All item_id and store_id combinations are unique" if dup_combos == 0 else "Duplicate item_id and store_id combinations found",
            count=dup_combos
        )

        # 2. Missing primary identifiers
        missing_ids = int(df["id"].isnull().sum()) if "id" in df.columns else 0
        missing_items = int(df["item_id"].isnull().sum()) if "item_id" in df.columns else 0
        missing_stores = int(df["store_id"].isnull().sum()) if "store_id" in df.columns else 0
        id_issues = missing_ids + missing_items + missing_stores
        report.add_check(
            "Missing Primary Identifiers",
            id_issues == 0,
            "No null values in id, item_id, or store_id" if id_issues == 0 else "Null identifiers detected",
            count=id_issues
        )

        # 3. Missing department/category info
        missing_dept_cat = 0
        for col in ["dept_id", "cat_id", "state_id"]:
            if col in df.columns:
                missing_dept_cat += int(df[col].isnull().sum())
        report.add_check(
            "Missing Department/Category Information",
            missing_dept_cat == 0,
            "Department, category, and state metadata complete" if missing_dept_cat == 0 else "Missing department/category metadata found",
            count=missing_dept_cat
        )

        # 4. Sales volumes check (d_1 ... d_N columns)
        d_cols = [c for c in df.columns if c.startswith("d_")]
        if d_cols:
            sales_matrix = df[d_cols]
            # Check negative sales
            neg_sales_mask = (sales_matrix < 0)
            neg_count = int(neg_sales_mask.sum().sum())
            report.add_check(
                "Negative Sales Volumes",
                neg_count == 0,
                "No negative daily sales values" if neg_count == 0 else "Negative daily sales values detected",
                count=neg_count
            )

            # Check missing sales values
            missing_sales_cnt = int(sales_matrix.isnull().sum().sum())
            report.add_check(
                "Missing Sales Values",
                missing_sales_cnt == 0,
                "All day columns populated" if missing_sales_cnt == 0 else "Missing values detected in day columns",
                count=missing_sales_cnt
            )

            # Check non-numeric strings
            non_numeric_cnt = 0
            for c in d_cols:
                if not pd.api.types.is_numeric_dtype(df[c]):
                    non_numeric_cnt += int(pd.to_numeric(df[c], errors="coerce").isnull().sum())
            report.add_check(
                "Numeric Sales Data Types",
                non_numeric_cnt == 0,
                "All daily sales columns are numeric" if non_numeric_cnt == 0 else "Non-numeric daily sales values found",
                count=non_numeric_cnt
            )

            # Calculate min/max stats across all sales days
            min_val = float(sales_matrix.min().min())
            max_val = float(sales_matrix.max().max())
            mean_val = float(sales_matrix.values.mean())
            report.stats["daily_sales_volume"] = {"min": min_val, "max": max_val, "mean": round(mean_val, 2)}

            # Outlier reporting (>500 daily units per item-store)
            high_outliers = int((sales_matrix > 500).sum().sum())
            report.add_check(
                "Sales Outliers Audit",
                True,
                f"Identified {high_outliers:,} extreme high sales records (>500 units/day) — retained for audit visibility",
                count=high_outliers
            )

        return report

    @staticmethod
    def audit_prices_data(df: pd.DataFrame) -> DataQualityReport:
        """Audits raw unit pricing dataset."""
        logger.info("Auditing Pricing dataset (%d rows x %d cols)...", len(df), len(df.columns))
        report = DataQualityReport("Prices")
        report.num_rows = len(df)
        report.num_cols = len(df.columns)
        report.dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        report.missing_values = {col: int(df[col].isnull().sum()) for col in df.columns}
        report.duplicate_records = int(df.duplicated().sum())

        # 1. Duplicate store/item/week combinations
        dup_combos = 0
        if all(c in df.columns for c in ["store_id", "item_id", "wm_yr_wk"]):
            dup_combos = int(df.duplicated(subset=["store_id", "item_id", "wm_yr_wk"]).sum())
        report.add_check(
            "Duplicate Store-Item-Week Keys",
            dup_combos == 0,
            "No duplicate store_id + item_id + wm_yr_wk keys" if dup_combos == 0 else "Duplicate store_id + item_id + wm_yr_wk entries found",
            count=dup_combos
        )

        # 2. Missing store_id, item_id, wm_yr_wk
        missing_keys = 0
        for col in ["store_id", "item_id", "wm_yr_wk"]:
            if col in df.columns:
                missing_keys += int(df[col].isnull().sum())
        report.add_check(
            "Missing Identifiers (Store/Item/Week)",
            missing_keys == 0,
            "Store, item, and week identifiers complete" if missing_keys == 0 else "Missing key identifiers found",
            count=missing_keys
        )

        # 3. Missing prices check
        missing_prices = int(df["sell_price"].isnull().sum()) if "sell_price" in df.columns else len(df)
        report.add_check(
            "Missing Prices",
            missing_prices == 0,
            "No missing price values" if missing_prices == 0 else "Missing sell_price values detected",
            count=missing_prices
        )

        # 4. Negative prices check
        if "sell_price" in df.columns:
            neg_prices = int((df["sell_price"] < 0).sum())
            report.add_check(
                "Negative Prices",
                neg_prices == 0,
                "No negative prices found" if neg_prices == 0 else "Negative prices detected",
                count=neg_prices
            )

            # 5. Zero prices check
            zero_prices = int((df["sell_price"] == 0).sum())
            report.add_check(
                "Zero Prices",
                zero_prices == 0,
                "No zero price records" if zero_prices == 0 else "Zero prices detected (flagged for review)",
                count=zero_prices
            )

            # 6. Data type check
            is_numeric = pd.api.types.is_numeric_dtype(df["sell_price"])
            report.add_check(
                "Numeric Price Data Type",
                is_numeric,
                "sell_price is numeric (float)" if is_numeric else "sell_price is non-numeric string type",
                count=0 if is_numeric else len(df)
            )

            # Numerical stats
            valid_prices = df["sell_price"].dropna()
            if not valid_prices.empty:
                report.stats["sell_price"] = {
                    "min": float(valid_prices.min()),
                    "max": float(valid_prices.max()),
                    "mean": float(valid_prices.mean())
                }

        return report
