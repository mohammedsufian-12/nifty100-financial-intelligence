from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


DB_PATH = Path("nifty100.db")

engine = create_engine(f"sqlite:///{DB_PATH}")

tables = [
    "analysis",
    "balance_sheet",
    "cash_flow",
    "companies",
    "documents",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "profit_loss",
    "pros_cons",
    "sectors",
    "stock_prices",
]

failures = []

for table in tables:
    df = pd.read_sql_table(table, engine)

    # Check completely empty rows
    empty_rows = df.isna().all(axis=1).sum()

    if empty_rows > 0:
        failures.append(
            {
                "table": table,
                "check": "empty_rows",
                "count": int(empty_rows),
                "status": "FAIL",
            }
        )

    # Check duplicate rows
    duplicates = df.duplicated().sum()

    if duplicates > 0:
        failures.append(
            {
                "table": table,
                "check": "duplicate_rows",
                "count": int(duplicates),
                "status": "FAIL",
            }
        )

    # Check missing values
    missing = df.isna().sum().sum()

    if missing > 0:
        failures.append(
            {
                "table": table,
                "check": "missing_values",
                "count": int(missing),
                "status": "FAIL",
            }
        )


if failures:
    result = pd.DataFrame(failures)
else:
    result = pd.DataFrame(
        columns=["table", "check", "count", "status"]
    )

result.to_csv("validation_failures.csv", index=False)

print("\nDATA QUALITY CHECK COMPLETE")
print("=" * 60)

if result.empty:
    print("NO VALIDATION FAILURES FOUND")
else:
    print(result.to_string(index=False))

print("\nSaved: validation_failures.csv")