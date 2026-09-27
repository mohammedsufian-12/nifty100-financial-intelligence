from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


# ============================================================
# Configuration
# ============================================================

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


# ============================================================
# General Data Quality Checks
# ============================================================

for table in tables:
    df = pd.read_sql_table(table, engine)

    # Empty rows
    empty_rows = df.isna().all(axis=1).sum()

    if empty_rows > 0:
        failures.append(
            {
                "table": table,
                "check": "empty_rows",
                "count": int(empty_rows),
                "status": "FAIL",
                "details": "",
            }
        )

    # Duplicate rows
    duplicates = df.duplicated().sum()

    if duplicates > 0:
        failures.append(
            {
                "table": table,
                "check": "duplicate_rows",
                "count": int(duplicates),
                "status": "FAIL",
                "details": "",
            }
        )

    # Missing values
    missing = df.isna().sum().sum()

    if missing > 0:
        failures.append(
            {
                "table": table,
                "check": "missing_values",
                "count": int(missing),
                "status": "FAIL",
                "details": "",
            }
        )


# ============================================================
# DQ-01: Company PK Uniqueness
# ============================================================

companies = pd.read_sql_table("companies", engine)

duplicate_company_ids = companies["id"].duplicated().sum()

if duplicate_company_ids > 0:
    failures.append(
        {
            "table": "companies",
            "check": "DQ-01_COMPANY_PK_UNIQUENESS",
            "count": int(duplicate_company_ids),
            "status": "CRITICAL",
            "details": "",
        }
    )

print(f"\nDQ-01: Duplicate company IDs = {duplicate_company_ids}")


# ============================================================
# DQ-02: Annual PK Uniqueness
# ============================================================

annual_tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
]

for table in annual_tables:
    df = pd.read_sql_table(table, engine)

    duplicate_keys = df.duplicated(
        subset=["company_id", "year"]
    ).sum()

    if duplicate_keys > 0:
        failures.append(
            {
                "table": table,
                "check": "DQ-02_ANNUAL_PK_UNIQUENESS",
                "count": int(duplicate_keys),
                "status": "CRITICAL",
                "details": "",
            }
        )

    print(
        f"DQ-02: {table} duplicate "
        f"(company_id, year) = {duplicate_keys}"
    )


# ============================================================
# DQ-03: Foreign-Key Integrity
# ============================================================

valid_company_ids = set(
    companies["id"].dropna()
)

fk_tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "documents",
    "financial_ratios",
    "pros_cons",
    "analysis",
    "market_cap",
    "peer_groups",
    "sectors",
    "stock_prices",
]

for table in fk_tables:

    df = pd.read_sql_table(table, engine)

    if "company_id" not in df.columns:
        continue

    orphan_rows = df[
        df["company_id"].notna()
        & ~df["company_id"].isin(valid_company_ids)
    ]

    orphan_count = len(orphan_rows)

    if orphan_count > 0:

        orphan_ids = sorted(
            orphan_rows["company_id"]
            .dropna()
            .astype(str)
            .unique()
        )

        failures.append(
            {
                "table": table,
                "check": "DQ-03_FOREIGN_KEY_INTEGRITY",
                "count": int(orphan_count),
                "status": "CRITICAL",
                "details": ", ".join(orphan_ids),
            }
        )

    print(
        f"DQ-03: {table} orphan rows = "
        f"{orphan_count}"
    )

# ============================================================
# DQ-04: Balance Sheet Balance
# ============================================================

balance_sheet = pd.read_sql_table(
    "balance_sheet",
    engine
)

balance_sheet["total_assets"] = pd.to_numeric(
    balance_sheet["total_assets"],
    errors="coerce"
)

balance_sheet["total_liabilities"] = pd.to_numeric(
    balance_sheet["total_liabilities"],
    errors="coerce"
)

valid_balance = balance_sheet[
    balance_sheet["total_assets"].notna()
    & balance_sheet["total_liabilities"].notna()
    & (balance_sheet["total_assets"] != 0)
].copy()

valid_balance["balance_difference_pct"] = (
    (
        valid_balance["total_assets"]
        - valid_balance["total_liabilities"]
    ).abs()
    / valid_balance["total_assets"].abs()
) * 100

balance_failures = valid_balance[
    valid_balance["balance_difference_pct"] >= 1.0
]

balance_failure_count = len(balance_failures)

if balance_failure_count > 0:

    failure_ids = sorted(
        balance_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "balance_sheet",
            "check": "DQ-04_BALANCE_SHEET_BALANCE",
            "count": int(balance_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-04: Balance sheet imbalance rows = "
    f"{balance_failure_count}"
)
# ============================================================
# DQ-05: OPM Cross-Check
# ============================================================

profit_loss = pd.read_sql_table(
    "profit_loss",
    engine
)

opm_columns = [
    "sales",
    "operating_profit",
    "opm_percentage",
]

if all(column in profit_loss.columns for column in opm_columns):

    profit_loss["sales"] = pd.to_numeric(
        profit_loss["sales"],
        errors="coerce"
    )

    profit_loss["operating_profit"] = pd.to_numeric(
        profit_loss["operating_profit"],
        errors="coerce"
    )

    profit_loss["opm_percentage"] = pd.to_numeric(
        profit_loss["opm_percentage"],
        errors="coerce"
    )

    valid_opm = profit_loss[
        profit_loss["sales"].notna()
        & profit_loss["operating_profit"].notna()
        & profit_loss["opm_percentage"].notna()
        & (profit_loss["sales"] != 0)
    ].copy()

    valid_opm["computed_opm"] = (
        valid_opm["operating_profit"]
        / valid_opm["sales"]
    ) * 100

    valid_opm["opm_difference"] = (
        valid_opm["opm_percentage"]
        - valid_opm["computed_opm"]
    ).abs()

    opm_failures = valid_opm[
        valid_opm["opm_difference"] >= 1.0
    ]

    opm_failure_count = len(opm_failures)

    if opm_failure_count > 0:

        failure_ids = sorted(
            opm_failures["company_id"]
            .dropna()
            .astype(str)
            .unique()
        )

        failures.append(
            {
                "table": "profit_loss",
                "check": "DQ-05_OPM_CROSS_CHECK",
                "count": int(opm_failure_count),
                "status": "WARNING",
                "details": ", ".join(failure_ids),
            }
        )

else:

    opm_failure_count = 0

    print(
        "DQ-05: Required OPM columns not found"
    )

print(
    f"DQ-05: OPM mismatch rows = "
    f"{opm_failure_count}"
)# ============================================================
# DQ-06: Positive Sales
# ============================================================

companies = pd.read_sql_table(
    "companies",
    engine
)

profit_loss = pd.read_sql_table(
    "profit_loss",
    engine
)

# Identify banks using the company name.
# Bank companies are excluded from the positive-sales check.
bank_ids = set(
    companies[
        companies["company_name"]
        .astype(str)
        .str.contains("bank", case=False, na=False)
    ]["id"]
)

non_bank_pl = profit_loss[
    ~profit_loss["company_id"].isin(bank_ids)
].copy()

non_bank_pl["sales"] = pd.to_numeric(
    non_bank_pl["sales"],
    errors="coerce"
)

sales_failures = non_bank_pl[
    non_bank_pl["sales"].notna()
    & (non_bank_pl["sales"] <= 0)
]

sales_failure_count = len(sales_failures)

if sales_failure_count > 0:

    failure_ids = sorted(
        sales_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "profit_loss",
            "check": "DQ-06_POSITIVE_SALES",
            "count": int(sales_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-06: Non-bank sales <= 0 rows = "
    f"{sales_failure_count}"
)
# ============================================================
# DQ-07: Year Format
# ============================================================

import re

annual_year_tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
]

invalid_year_records = []
ttm_count = 0

for table in annual_year_tables:

    df = pd.read_sql_table(
        table,
        engine
    )

    if "year" not in df.columns:
        continue

    for _, row in df.iterrows():

        raw_year = row["year"]

        if pd.isna(raw_year):

            invalid_year_records.append(
                {
                    "table": table,
                    "company_id": row.get("company_id"),
                    "year": "MISSING",
                }
            )

            continue

        year_text = str(raw_year).strip()

        # TTM = trailing twelve months.
        # It is valid data but not an annual financial year.
        if year_text.upper() == "TTM":
            ttm_count += 1
            continue

        valid = False

        # Examples:
        # 2013
        # 2024
        # 2024.5
        if re.fullmatch(
            r"\d{4}(\.\d+)?",
            year_text
        ):
            valid = True

        # Examples:
        # Mar-13
        # Mar-2018
        # Mar 2016 9m
        # Mar 2023 15
        elif re.match(
            r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ -]\d{2,4}",
            year_text,
            re.IGNORECASE,
        ):
            valid = True

        if not valid:

            invalid_year_records.append(
                {
                    "table": table,
                    "company_id": row.get("company_id"),
                    "year": year_text,
                }
            )

invalid_year_count = len(
    invalid_year_records
)

if invalid_year_count > 0:

    invalid_details = sorted(
        set(
            f"{item['table']}:{item['year']}"
            for item in invalid_year_records
        )
    )

    failures.append(
        {
            "table": "annual_financial_tables",
            "check": "DQ-07_YEAR_FORMAT",
            "count": int(invalid_year_count),
            "status": "CRITICAL",
            "details": ", ".join(invalid_details),
        }
    )

print(
    f"DQ-07: Invalid year rows = "
    f"{invalid_year_count}"
)

print(
    f"DQ-07: TTM rows documented = "
    f"{ttm_count}"
)
# ============================================================
# DQ-08: Ticker Format
# ============================================================

companies = pd.read_sql_table(
    "companies",
    engine
)

invalid_tickers = []

for _, row in companies.iterrows():

    raw_ticker = row["id"]

    if pd.isna(raw_ticker):

        invalid_tickers.append(
            {
                "ticker": "MISSING",
                "reason": "Missing company ID",
            }
        )

        continue

    ticker = str(raw_ticker).strip().upper()

    # Ticker must contain 2–12 characters.
    if not (2 <= len(ticker) <= 12):

        invalid_tickers.append(
            {
                "ticker": ticker,
                "reason": "Length outside 2–12 characters",
            }
        )

invalid_ticker_count = len(
    invalid_tickers
)

if invalid_ticker_count > 0:

    ticker_details = sorted(
        set(
            f"{item['ticker']} ({item['reason']})"
            for item in invalid_tickers
        )
    )

    failures.append(
        {
            "table": "companies",
            "check": "DQ-08_TICKER_FORMAT",
            "count": int(invalid_ticker_count),
            "status": "CRITICAL",
            "details": ", ".join(ticker_details),
        }
    )

print(
    f"DQ-08: Invalid ticker rows = "
    f"{invalid_ticker_count}"
)
# ============================================================
# DQ-09: Net Cash Check
# ============================================================

cash_flow = pd.read_sql_table(
    "cash_flow",
    engine
)

cash_columns = [
    "operating_activity",
    "investing_activity",
    "financing_activity",
    "net_cash_flow",
]

if all(
    column in cash_flow.columns
    for column in cash_columns
):

    for column in cash_columns:

        cash_flow[column] = pd.to_numeric(
            cash_flow[column],
            errors="coerce"
        )

    valid_cash_flow = cash_flow[
        cash_flow[
            [
                "operating_activity",
                "investing_activity",
                "financing_activity",
                "net_cash_flow",
            ]
        ].notna().all(axis=1)
    ].copy()

    valid_cash_flow["computed_net_cash"] = (
        valid_cash_flow["operating_activity"]
        + valid_cash_flow["investing_activity"]
        + valid_cash_flow["financing_activity"]
    )

    valid_cash_flow["cash_difference"] = (
        valid_cash_flow["net_cash_flow"]
        - valid_cash_flow["computed_net_cash"]
    ).abs()

    cash_failures = valid_cash_flow[
        valid_cash_flow["cash_difference"] > 10
    ]

    cash_failure_count = len(
        cash_failures
    )

    if cash_failure_count > 0:

        failure_ids = sorted(
            cash_failures["company_id"]
            .dropna()
            .astype(str)
            .unique()
        )

        failures.append(
            {
                "table": "cash_flow",
                "check": "DQ-09_NET_CASH_CHECK",
                "count": int(cash_failure_count),
                "status": "WARNING",
                "details": ", ".join(failure_ids),
            }
        )

else:

    cash_failure_count = 0

    print(
        "DQ-09: Required cash-flow columns not found"
    )

print(
    f"DQ-09: Net cash mismatch rows = "
    f"{cash_failure_count}"
)
# ============================================================
# DQ-10: Non-Negative Fixed Assets
# ============================================================

balance_sheet = pd.read_sql_table(
    "balance_sheet",
    engine
)

balance_sheet["fixed_assets"] = pd.to_numeric(
    balance_sheet["fixed_assets"],
    errors="coerce"
)

fixed_asset_failures = balance_sheet[
    balance_sheet["fixed_assets"].notna()
    & (balance_sheet["fixed_assets"] < 0)
]

fixed_asset_failure_count = len(
    fixed_asset_failures
)

if fixed_asset_failure_count > 0:

    failure_ids = sorted(
        fixed_asset_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "balance_sheet",
            "check": "DQ-10_NON_NEGATIVE_FIXED_ASSETS",
            "count": int(fixed_asset_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-10: Negative fixed asset rows = "
    f"{fixed_asset_failure_count}"
)
# ============================================================
# DQ-11: Tax Rate Range
# ============================================================

profit_loss = pd.read_sql_table(
    "profit_loss",
    engine
)

profit_loss["tax_percentage"] = pd.to_numeric(
    profit_loss["tax_percentage"],
    errors="coerce"
)

tax_failures = profit_loss[
    profit_loss["tax_percentage"].notna()
    & (
        (profit_loss["tax_percentage"] < 0)
        | (profit_loss["tax_percentage"] > 60)
    )
]

tax_failure_count = len(
    tax_failures
)

if tax_failure_count > 0:

    failure_ids = sorted(
        tax_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "profit_loss",
            "check": "DQ-11_TAX_RATE_RANGE",
            "count": int(tax_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-11: Tax rate out-of-range rows = "
    f"{tax_failure_count}"
)
# ============================================================
# DQ-12: Dividend Payout Cap
# ============================================================

profit_loss = pd.read_sql_table(
    "profit_loss",
    engine
)

profit_loss["dividend_payout"] = pd.to_numeric(
    profit_loss["dividend_payout"],
    errors="coerce"
)

dividend_failures = profit_loss[
    profit_loss["dividend_payout"].notna()
    & (profit_loss["dividend_payout"] > 200)
]

dividend_failure_count = len(
    dividend_failures
)

if dividend_failure_count > 0:

    failure_ids = sorted(
        dividend_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "profit_loss",
            "check": "DQ-12_DIVIDEND_PAYOUT_CAP",
            "count": int(dividend_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-12: Dividend payout >200% rows = "
    f"{dividend_failure_count}"
)
# ============================================================
# DQ-13: Annual Report URL Validity
# ============================================================

documents = pd.read_sql_table(
    "documents",
    engine
)

missing_urls = documents[
    "annual_report"
].isna().sum()

if missing_urls > 0:

    failures.append(
        {
            "table": "documents",
            "check": "DQ-13_URL_VALIDITY",
            "count": int(missing_urls),
            "status": "WARNING",
            "details": "Missing annual report URLs",
        }
    )

print(
    f"\nDQ-13: Missing annual report URLs = "
    f"{missing_urls}"
)
# ============================================================
# DQ-14: EPS Sign Consistency
# ============================================================

profit_loss = pd.read_sql_table(
    "profit_loss",
    engine
)

profit_loss["net_profit"] = pd.to_numeric(
    profit_loss["net_profit"],
    errors="coerce"
)

profit_loss["eps"] = pd.to_numeric(
    profit_loss["eps"],
    errors="coerce"
)

eps_failures = profit_loss[
    profit_loss["net_profit"].notna()
    & profit_loss["eps"].notna()
    & (
        (
            (profit_loss["net_profit"] > 0)
            & (profit_loss["eps"] <= 0)
        )
        |
        (
            (profit_loss["net_profit"] < 0)
            & (profit_loss["eps"] >= 0)
        )
    )
]

eps_failure_count = len(
    eps_failures
)

if eps_failure_count > 0:

    failure_ids = sorted(
        eps_failures["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    failures.append(
        {
            "table": "profit_loss",
            "check": "DQ-14_EPS_SIGN_CONSISTENCY",
            "count": int(eps_failure_count),
            "status": "WARNING",
            "details": ", ".join(failure_ids),
        }
    )

print(
    f"DQ-14: EPS sign mismatch rows = "
    f"{eps_failure_count}"
)
# ============================================================
# DQ-15: BSE/ASE Balance
# ============================================================

balance_sheet = pd.read_sql_table(
    "balance_sheet",
    engine
)

balance_sheet["total_assets"] = pd.to_numeric(
    balance_sheet["total_assets"],
    errors="coerce"
)

balance_sheet["total_liabilities"] = pd.to_numeric(
    balance_sheet["total_liabilities"],
    errors="coerce"
)

valid_balance_strict = balance_sheet[
    balance_sheet["total_assets"].notna()
    & balance_sheet["total_liabilities"].notna()
].copy()

strict_balance_failures = valid_balance_strict[
    valid_balance_strict["total_assets"]
    != valid_balance_strict["total_liabilities"]
]

strict_balance_failure_count = len(
    strict_balance_failures
)

print(
    f"DQ-15: Strict asset/liability mismatch rows = "
    f"{strict_balance_failure_count}"
)# ============================================================
# DQ-16: Coverage Check
# ============================================================

coverage_failures = []

for table in ["profit_loss", "balance_sheet", "cash_flow"]:
    df = pd.read_sql_table(table, engine)

    coverage = (
        df.groupby("company_id")["year_normalized"]
        .nunique()
        .reset_index(name="year_count")
    )

    insufficient = coverage[
        coverage["year_count"] < 5
    ]

    for _, row in insufficient.iterrows():
        coverage_failures.append({
            "table": table,
            "company_id": row["company_id"],
            "year_count": int(row["year_count"])
        })

# Unique companies with insufficient coverage
unique_coverage_failures = {}

for item in coverage_failures:
    company_id = item["company_id"]

    if company_id not in unique_coverage_failures:
        unique_coverage_failures[company_id] = []

    unique_coverage_failures[company_id].append(
        f"{item['table']} ({item['year_count']} years)"
    )

coverage_failure_count = len(unique_coverage_failures)

if coverage_failure_count > 0:
    details = ", ".join(
        f"{company_id}: {', '.join(tables)}"
        for company_id, tables in unique_coverage_failures.items()
    )

    failures.append({
        "table": "financial_coverage",
        "check": "DQ-16_COVERAGE_CHECK",
        "count": coverage_failure_count,
        "status": "WARNING",
        "details": details
    })

print(
    f"DQ-16: Companies with <5 years coverage = "
    f"{coverage_failure_count}"
)
# DQ-15 is informational only.
# It is intentionally NOT added to validation_failures.csv.
# ============================================================
# Save Validation Results
# ============================================================

if failures:

    result = pd.DataFrame(failures)

else:

    result = pd.DataFrame(
        columns=[
            "table",
            "check",
            "count",
            "status",
            "details",
        ]
    )


result.to_csv(
    "validation_failures.csv",
    index=False
)


# ============================================================
# Final Output
# ============================================================

print("\nDATA QUALITY CHECK COMPLETE")
print("=" * 60)

if result.empty:

    print("NO VALIDATION FAILURES FOUND")

else:

    print(
        result.to_string(index=False)
    )

print(
    "\nSaved: validation_failures.csv"
)