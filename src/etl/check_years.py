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
    print(f"\n--- {table} ---")

    rows = connection.execute(
        f"SELECT DISTINCT year FROM {table} ORDER BY year"
    ).fetchall()

    print([row[0] for row in rows])

connection.close()