from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


RAW_DIR = Path("data/raw")
DB_PATH = Path("nifty100.db")

HEADER_1_FILES = {
    "analysis.xlsx": "analysis",
    "balancesheet.xlsx": "balance_sheet",
    "cashflow.xlsx": "cash_flow",
    "companies.xlsx": "companies",
    "documents.xlsx": "documents",
    "profitandloss.xlsx": "profit_loss",
    "prosandcons.xlsx": "pros_cons",
}

HEADER_0_FILES = {
    "financial_ratios.xlsx": "financial_ratios",
    "market_cap.xlsx": "market_cap",
    "peer_groups.xlsx": "peer_groups",
    "sectors.xlsx": "sectors",
    "stock_prices.xlsx": "stock_prices",
}


def load_excel(file_name, table_name, header):
    """Load one Excel file into SQLite."""
    file_path = RAW_DIR / file_name

    df = pd.read_excel(
        file_path,
        sheet_name=0,
        header=header,
    )

    df.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    df.to_sql(
        table_name,
        con=engine,
        if_exists="replace",
        index=False,
    )

    return len(df)


engine = create_engine(f"sqlite:///{DB_PATH}")

audit_rows = []

for file_name, table_name in HEADER_1_FILES.items():
    try:
        rows = load_excel(file_name, table_name, header=1)

        audit_rows.append(
            {
                "file": file_name,
                "table": table_name,
                "rows": rows,
                "status": "SUCCESS",
            }
        )

    except Exception as error:
        audit_rows.append(
            {
                "file": file_name,
                "table": table_name,
                "rows": 0,
                "status": f"FAILED: {error}",
            }
        )


for file_name, table_name in HEADER_0_FILES.items():
    try:
        rows = load_excel(file_name, table_name, header=0)

        audit_rows.append(
            {
                "file": file_name,
                "table": table_name,
                "rows": rows,
                "status": "SUCCESS",
            }
        )

    except Exception as error:
        audit_rows.append(
            {
                "file": file_name,
                "table": table_name,
                "rows": 0,
                "status": f"FAILED: {error}",
            }
        )


audit_df = pd.DataFrame(audit_rows)

audit_df.to_csv(
    "load_audit.csv",
    index=False,
)

print("\nDATA LOAD COMPLETE")
print("=" * 60)
print(audit_df.to_string(index=False))