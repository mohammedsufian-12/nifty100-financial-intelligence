import sqlite3
import pandas as pd


DB_PATH = "nifty100.db"

tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "financial_ratios",
    "market_cap",
]


def normalize_year(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.upper() == "TTM":
        return None

    for year in range(2011, 2026):
        if str(year) in text:
            return year

    return None


connection = sqlite3.connect(DB_PATH)

for table in tables:
    df = pd.read_sql_query(
        f"SELECT * FROM {table}",
        connection,
    )

    if "year" in df.columns:
        df["year_normalized"] = df["year"].apply(normalize_year)

        df.to_sql(
            table,
            connection,
            if_exists="replace",
            index=False,
        )

        print(f"{table}: normalized")

connection.close()

print("\nYEAR NORMALIZATION COMPLETE")