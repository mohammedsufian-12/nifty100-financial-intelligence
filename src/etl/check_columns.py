import sqlite3

connection = sqlite3.connect("nifty100.db")

tables = [
    "companies",
    "balance_sheet",
    "cash_flow",
    "profit_loss",
    "financial_ratios",
    "market_cap",
    "sectors",
]

for table in tables:
    print(f"\n--- {table} ---")

    columns = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    for column in columns:
        print(column[1])

connection.close()