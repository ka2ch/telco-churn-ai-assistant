"""
Step 1: Load the raw Telco CSV, clean it, and save it into a SQLite database
split into three tables (customers, services, billing).

Run from the project folder:
    python src/load_data.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

# --- File locations (works no matter where you run it from) ---
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
DB_PATH = ROOT / "data" / "telco.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def yes_no_to_int(series: pd.Series) -> pd.Series:
    """'Yes' -> 1, anything else ('No', 'No internet service', ...) -> 0."""
    return (series == "Yes").astype(int)


def load_and_clean() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Can't find the data file:\n  {CSV_PATH}\n"
            "Download it from Kaggle and put it in the data/ folder."
        )

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} rows from the CSV")

    # TotalCharges has a few blank values (brand-new customers with 0 months).
    # Turn blanks into numbers; a new customer has paid nothing yet -> 0.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    blanks = df["TotalCharges"].isna().sum()
    df["TotalCharges"] = df["TotalCharges"].fillna(0.0)
    print(f"Fixed {blanks} blank TotalCharges values (set to 0)")

    return df


def split_into_tables(df: pd.DataFrame):
    customers = pd.DataFrame({
        "customer_id": df["customerID"],
        "gender": df["gender"],
        "senior_citizen": df["SeniorCitizen"].astype(int),
        "has_partner": yes_no_to_int(df["Partner"]),
        "has_dependents": yes_no_to_int(df["Dependents"]),
        "tenure_months": df["tenure"].astype(int),
        "churned": yes_no_to_int(df["Churn"]),
    })

    services = pd.DataFrame({
        "customer_id": df["customerID"],
        "phone_service": yes_no_to_int(df["PhoneService"]),
        "multiple_lines": yes_no_to_int(df["MultipleLines"]),
        "internet_service": df["InternetService"],
        "online_security": yes_no_to_int(df["OnlineSecurity"]),
        "online_backup": yes_no_to_int(df["OnlineBackup"]),
        "device_protection": yes_no_to_int(df["DeviceProtection"]),
        "tech_support": yes_no_to_int(df["TechSupport"]),
        "streaming_tv": yes_no_to_int(df["StreamingTV"]),
        "streaming_movies": yes_no_to_int(df["StreamingMovies"]),
    })

    billing = pd.DataFrame({
        "customer_id": df["customerID"],
        "contract": df["Contract"],
        "paperless_billing": yes_no_to_int(df["PaperlessBilling"]),
        "payment_method": df["PaymentMethod"],
        "monthly_charges": df["MonthlyCharges"].astype(float),
        "total_charges": df["TotalCharges"].astype(float),
    })

    return customers, services, billing


def save_to_database(customers, services, billing):
    with sqlite3.connect(DB_PATH) as conn:
        # Create the empty tables from schema.sql
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # Fill them
        customers.to_sql("customers", conn, if_exists="append", index=False)
        services.to_sql("services", conn, if_exists="append", index=False)
        billing.to_sql("billing", conn, if_exists="append", index=False)

    print(f"Saved database to {DB_PATH}")


def quick_check():
    """Print a few numbers so we know the data went in correctly."""
    with sqlite3.connect(DB_PATH) as conn:
        for table in ["customers", "services", "billing"]:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<10} {n:,} rows")

        print("\nChurn rate by contract type:")
        result = pd.read_sql_query(
            """
            SELECT b.contract,
                   COUNT(*)                         AS customers,
                   ROUND(AVG(c.churned) * 100, 1)   AS churn_rate_pct
            FROM customers c
            JOIN billing b ON c.customer_id = b.customer_id
            GROUP BY b.contract
            ORDER BY churn_rate_pct DESC
            """,
            conn,
        )
        print(result.to_string(index=False))


if __name__ == "__main__":
    df = load_and_clean()
    customers, services, billing = split_into_tables(df)
    save_to_database(customers, services, billing)
    print("\nCheck:")
    quick_check()
