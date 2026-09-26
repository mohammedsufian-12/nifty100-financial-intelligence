import sqlite3

connection = sqlite3.connect("nifty100.db")

tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "financial_ratios",
    "market_cap",
]

for table in tables:
    total = connection.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    valid = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE year_normalized IS NOT NULL
        """
    ).fetchone()[0]

    print(f"{table}: {valid} / {total}")

connection.close()