import sqlite3
import pandas as pd


DB_PATH = "nifty100.db"

TABLES = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "financial_ratios",
    "market_cap",
]


def normalize_year(value):
    """Convert financial year labels into a four-digit year."""
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.upper() == "TTM":
        return None

    for year in range(2011, 2026):
        if str(year) in text:
            return year

    return None


def normalize_ticker(value):
    """Normalize company ticker symbols."""
    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    for suffix in [".NS", "-EQ", ".EQ"]:
        if text.endswith(suffix):
            text = text[:-len(suffix)]

    text = text.replace(" ", "")
    text = text.replace("-", "_")

    return text


def main():
    """Normalize year columns in the financial tables."""
    connection = sqlite3.connect(DB_PATH)

    try:
        for table in TABLES:
            df = pd.read_sql_query(
                f"SELECT * FROM {table}",
                connection,
            )

            if "year" in df.columns:
                df["year_normalized"] = df["year"].apply(
                    normalize_year
                )

                df.to_sql(
                    table,
                    connection,
                    if_exists="replace",
                    index=False,
                )

                print(f"{table}: normalized")

    finally:
        connection.close()

    print("\nYEAR NORMALIZATION COMPLETE")


if __name__ == "__main__":
    main()
