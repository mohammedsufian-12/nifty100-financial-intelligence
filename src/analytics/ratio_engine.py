import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


DB_PATH = "nifty100.db"
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RATIO_OUTPUT = OUTPUT_DIR / "financial_ratios_calculated.csv"
CAPITAL_OUTPUT = OUTPUT_DIR / "capital_allocation.csv"
EDGE_LOG = OUTPUT_DIR / "ratio_edge_cases.log"


def safe_divide(numerator, denominator):
    """Safely divide two series and return NaN when denominator is zero."""
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def yoy_growth(series):
    """Calculate year-over-year percentage growth."""
    return series.pct_change(fill_method=None) * 100


def safe_cagr(start, end, years):
    """Calculate CAGR only when start and end values are positive."""
    if pd.isna(start) or pd.isna(end) or start <= 0 or end <= 0:
        return np.nan

    return ((end / start) ** (1 / years) - 1) * 100


def calculate_cagr(group, column, years):
    """Calculate rolling CAGR for a financial column."""
    values = group[column].to_numpy(dtype=float)
    result = np.full(len(values), np.nan)

    for i in range(years, len(values)):
        start = values[i - years]
        end = values[i]

        result[i] = safe_cagr(start, end, years)

    return pd.Series(result, index=group.index)


def main():
    connection = sqlite3.connect(DB_PATH)

    print("Loading financial data...")

    profit_loss = pd.read_sql_query(
        "SELECT * FROM profit_loss",
        connection,
    )

    balance_sheet = pd.read_sql_query(
        "SELECT * FROM balance_sheet",
        connection,
    )

    cash_flow = pd.read_sql_query(
        "SELECT * FROM cash_flow",
        connection,
    )

    market_cap = pd.read_sql_query(
        "SELECT * FROM market_cap",
        connection,
    )

    # ---------------------------------------------------------
    # Convert numeric columns
    # ---------------------------------------------------------

    profit_columns = [
        "sales",
        "expenses",
        "operating_profit",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "net_profit",
        "eps",
        "dividend_payout",
    ]

    balance_columns = [
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
    ]

    cash_columns = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for column in profit_columns:
        if column in profit_loss.columns:
            profit_loss[column] = pd.to_numeric(
                profit_loss[column],
                errors="coerce",
            )

    for column in balance_columns:
        if column in balance_sheet.columns:
            balance_sheet[column] = pd.to_numeric(
                balance_sheet[column],
                errors="coerce",
            )

    for column in cash_columns:
        if column in cash_flow.columns:
            cash_flow[column] = pd.to_numeric(
                cash_flow[column],
                errors="coerce",
            )

    # ---------------------------------------------------------
    # Keep only normalized years
    # ---------------------------------------------------------

    profit_loss = profit_loss[
        profit_loss["year_normalized"].notna()
    ].copy()

    balance_sheet = balance_sheet[
        balance_sheet["year_normalized"].notna()
    ].copy()

    cash_flow = cash_flow[
        cash_flow["year_normalized"].notna()
    ].copy()

    # ---------------------------------------------------------
    # Remove duplicate company-year rows
    # ---------------------------------------------------------

    profit_loss = profit_loss.drop_duplicates(
        subset=["company_id", "year_normalized"],
        keep="last",
    )

    balance_sheet = balance_sheet.drop_duplicates(
        subset=["company_id", "year_normalized"],
        keep="last",
    )

    cash_flow = cash_flow.drop_duplicates(
        subset=["company_id", "year_normalized"],
        keep="last",
    )

    # ---------------------------------------------------------
    # Merge financial statements
    # ---------------------------------------------------------

    df = profit_loss.merge(
        balance_sheet,
        on=["company_id", "year_normalized"],
        how="left",
        suffixes=("", "_bs"),
    )

    df = df.merge(
        cash_flow,
        on=["company_id", "year_normalized"],
        how="left",
        suffixes=("", "_cf"),
    )

    # ---------------------------------------------------------
    # Sort
    # ---------------------------------------------------------

    df = df.sort_values(
        ["company_id", "year_normalized"]
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # Base financial values
    # ---------------------------------------------------------

    df["total_equity"] = (
        df["equity_capital"].fillna(0)
        + df["reserves"].fillna(0)
    )

    df["ebit"] = (
        df["operating_profit"]
        - df["depreciation"].fillna(0)
    )

    # Project document uses operating profit as EBITDA proxy
    df["ebitda"] = df["operating_profit"]

    df["cfo"] = df["operating_activity"]
    df["cfi"] = df["investing_activity"]
    df["cff"] = df["financing_activity"]

    # CapEx is represented by absolute investing activity
    df["capex_cr"] = df["cfi"].abs()

    # FCF = CFO + CFI
    df["free_cash_flow_cr"] = (
        df["cfo"].fillna(0)
        + df["cfi"].fillna(0)
    )

    # ---------------------------------------------------------
    # 1. PROFITABILITY RATIOS
    # ---------------------------------------------------------

    df["net_profit_margin_pct"] = (
        safe_divide(
            df["net_profit"],
            df["sales"],
        )
        * 100
    )

    df["operating_profit_margin_pct"] = (
        safe_divide(
            df["operating_profit"],
            df["sales"],
        )
        * 100
    )

    df["ebit_margin_pct"] = (
        safe_divide(
            df["ebit"],
            df["sales"],
        )
        * 100
    )

    df["return_on_equity_pct"] = (
        safe_divide(
            df["net_profit"],
            df["total_equity"],
        )
        * 100
    )

    df["return_on_assets_pct"] = (
        safe_divide(
            df["net_profit"],
            df["total_assets"],
        )
        * 100
    )

    df["return_on_capital_employed_pct"] = (
        safe_divide(
            df["ebit"],
            df["total_equity"] + df["borrowings"],
        )
        * 100
    )

    # ---------------------------------------------------------
    # 2. LEVERAGE RATIOS
    # ---------------------------------------------------------

    df["debt_to_equity"] = safe_divide(
        df["borrowings"],
        df["total_equity"],
    )

    df["debt_to_assets_pct"] = (
        safe_divide(
            df["borrowings"],
            df["total_assets"],
        )
        * 100
    )

    df["liabilities_to_assets_pct"] = (
        safe_divide(
            df["total_liabilities"],
            df["total_assets"],
        )
        * 100
    )

    # Investments are used as liquid-asset proxy because
    # a separate cash field is not available.
    df["net_debt_cr"] = (
        df["borrowings"]
        - df["investments"].fillna(0)
    )

    df["net_debt_to_ebitda"] = safe_divide(
        df["net_debt_cr"],
        df["ebitda"],
    )

    interest_denominator = df["interest"].copy()

    df["interest_coverage"] = safe_divide(
        df["operating_profit"] + df["other_income"].fillna(0),
        interest_denominator,
    )

    # Debt-free companies
    debt_free = df["borrowings"].fillna(0) <= 0

    df.loc[
        debt_free,
        "interest_coverage",
    ] = 999.0

    # ---------------------------------------------------------
    # 3. EFFICIENCY RATIOS
    # ---------------------------------------------------------

    df["asset_turnover"] = safe_divide(
        df["sales"],
        df["total_assets"],
    )

    df["fixed_asset_turnover"] = safe_divide(
        df["sales"],
        df["fixed_assets"],
    )

    df["working_capital_proxy_cr"] = (
        df["other_asset"].fillna(0)
        - df["other_liabilities"].fillna(0)
    )

    df["working_capital_days"] = (
        safe_divide(
            df["working_capital_proxy_cr"],
            df["sales"],
        )
        * 365
    )

    # Project proxy because detailed inventory data
    # is not available.
    df["inventory_turnover_proxy"] = safe_divide(
        df["sales"],
        df["fixed_assets"],
    )

    # ---------------------------------------------------------
    # 4. CASH FLOW RATIOS
    # ---------------------------------------------------------

    df["cash_flow_to_profit"] = safe_divide(
        df["cfo"],
        df["net_profit"],
    )

    df["fcf_to_profit"] = safe_divide(
        df["free_cash_flow_cr"],
        df["net_profit"],
    )

    df["cfo_to_sales_pct"] = (
        safe_divide(
            df["cfo"],
            df["sales"],
        )
        * 100
    )

    df["fcf_margin_pct"] = (
        safe_divide(
            df["free_cash_flow_cr"],
            df["sales"],
        )
        * 100
    )

    df["capex_intensity_pct"] = (
        safe_divide(
            df["capex_cr"],
            df["sales"],
        )
        * 100
    )

    df["fcf_conversion_rate_pct"] = (
        safe_divide(
            df["free_cash_flow_cr"],
            df["ebitda"],
        )
        * 100
    )

    # ---------------------------------------------------------
    # 5. PER SHARE / DIVIDEND METRICS
    # ---------------------------------------------------------

    df["earnings_per_share"] = df["eps"]

    # Shares outstanding are not available.
    # Therefore this is explicitly a proxy.
    df["book_value_per_share_proxy"] = safe_divide(
        df["total_equity"],
        df["equity_capital"],
    )

    df["dividend_payout_ratio_pct"] = df[
        "dividend_payout"
    ]

    df["retained_profit_proxy"] = (
        df["net_profit"]
        * (
            1
            - df["dividend_payout_ratio_pct"].fillna(0)
            / 100
        )
    )

    # ---------------------------------------------------------
    # 6. YEAR-OVER-YEAR GROWTH
    # ---------------------------------------------------------

    grouped = df.groupby(
        "company_id",
        group_keys=False,
    )

    df["revenue_growth_pct"] = grouped["sales"].transform(
        yoy_growth
    )

    df["profit_growth_pct"] = grouped["net_profit"].transform(
        yoy_growth
    )

    df["operating_profit_growth_pct"] = grouped[
        "operating_profit"
    ].transform(yoy_growth)

    df["eps_growth_pct"] = grouped["eps"].transform(
        yoy_growth
    )

    df["cfo_growth_pct"] = grouped["cfo"].transform(
        yoy_growth
    )

    df["fcf_growth_pct"] = grouped[
        "free_cash_flow_cr"
    ].transform(yoy_growth)

    # ---------------------------------------------------------
    # 7. CAGR METRICS
    # ---------------------------------------------------------

    df["revenue_cagr_3y_pct"] = np.nan
    df["revenue_cagr_5y_pct"] = np.nan
    df["revenue_cagr_10y_pct"] = np.nan

    df["pat_cagr_3y_pct"] = np.nan
    df["pat_cagr_5y_pct"] = np.nan
    df["pat_cagr_10y_pct"] = np.nan

    df["eps_cagr_3y_pct"] = np.nan
    df["eps_cagr_5y_pct"] = np.nan
    df["eps_cagr_10y_pct"] = np.nan

    df["fcf_cagr_5y_pct"] = np.nan
    df["fcf_cagr_10y_pct"] = np.nan

    for company_id, group in df.groupby("company_id"):
        group = group.sort_values("year_normalized")

        for years, column, output in [
            (3, "sales", "revenue_cagr_3y_pct"),
            (5, "sales", "revenue_cagr_5y_pct"),
            (10, "sales", "revenue_cagr_10y_pct"),
            (3, "net_profit", "pat_cagr_3y_pct"),
            (5, "net_profit", "pat_cagr_5y_pct"),
            (10, "net_profit", "pat_cagr_10y_pct"),
            (3, "eps", "eps_cagr_3y_pct"),
            (5, "eps", "eps_cagr_5y_pct"),
            (10, "eps", "eps_cagr_10y_pct"),
            (5, "free_cash_flow_cr", "fcf_cagr_5y_pct"),
            (10, "free_cash_flow_cr", "fcf_cagr_10y_pct"),
        ]:
            calculated = calculate_cagr(
                group,
                column,
                years,
            )

            df.loc[
                calculated.index,
                output,
            ] = calculated

    # ---------------------------------------------------------
    # 8. BALANCE SHEET STRUCTURE
    # ---------------------------------------------------------

    df["reserves_to_equity_pct"] = (
        safe_divide(
            df["reserves"],
            df["total_equity"],
        )
        * 100
    )

    df["borrowings_to_assets_pct"] = (
        safe_divide(
            df["borrowings"],
            df["total_assets"],
        )
        * 100
    )

    df["fixed_assets_to_assets_pct"] = (
        safe_divide(
            df["fixed_assets"],
            df["total_assets"],
        )
        * 100
    )

    df["cwip_to_assets_pct"] = (
        safe_divide(
            df["cwip"],
            df["total_assets"],
        )
        * 100
    )

    df["investments_to_assets_pct"] = (
        safe_divide(
            df["investments"],
            df["total_assets"],
        )
        * 100
    )

    df["other_assets_to_assets_pct"] = (
        safe_divide(
            df["other_asset"],
            df["total_assets"],
        )
        * 100
    )

    df["equity_to_assets_pct"] = (
        safe_divide(
            df["total_equity"],
            df["total_assets"],
        )
        * 100
    )

    # ---------------------------------------------------------
    # 9. CASH FLOW STRUCTURE
    # ---------------------------------------------------------

    total_cash_flow = (
        df["cfo"].fillna(0)
        + df["cfi"].fillna(0)
        + df["cff"].fillna(0)
    )

    df["cfo_to_total_cash_flow_pct"] = (
        safe_divide(
            df["cfo"],
            total_cash_flow,
        )
        * 100
    )

    df["cfi_to_sales_pct"] = (
        safe_divide(
            df["cfi"],
            df["sales"],
        )
        * 100
    )

    df["cff_to_sales_pct"] = (
        safe_divide(
            df["cff"],
            df["sales"],
        )
        * 100
    )

    df["net_cash_flow_to_sales_pct"] = (
        safe_divide(
            df["net_cash_flow"],
            df["sales"],
        )
        * 100
    )

    # ---------------------------------------------------------
    # 10. CAPITAL ALLOCATION PATTERN
    # ---------------------------------------------------------

    df["CFO_sign"] = np.where(
        df["cfo"] > 0,
        "Positive",
        np.where(
            df["cfo"] < 0,
            "Negative",
            "Neutral",
        ),
    )

    df["CFI_sign"] = np.where(
        df["cfi"] > 0,
        "Positive",
        np.where(
            df["cfi"] < 0,
            "Negative",
            "Neutral",
        ),
    )

    df["CFF_sign"] = np.where(
        df["cff"] > 0,
        "Positive",
        np.where(
            df["cff"] < 0,
            "Negative",
            "Neutral",
        ),
    )

    def capital_pattern(row):
        cfo = row["CFO_sign"]
        cfi = row["CFI_sign"]
        cff = row["CFF_sign"]

        if cfo == "Positive" and cfi == "Negative" and cff == "Negative":
            return "Self-Funded Growth"

        if cfo == "Positive" and cfi == "Negative" and cff == "Positive":
            return "Debt/Capital Funded Growth"

        if cfo == "Positive" and cfi == "Positive" and cff == "Negative":
            return "Asset Monetization / Debt Reduction"

        if cfo == "Positive" and cfi == "Positive" and cff == "Positive":
            return "Strong Cash Generation"

        if cfo == "Negative" and cff == "Positive":
            return "External Funding / Potential Distress"

        if cfo == "Negative" and cfi == "Negative" and cff == "Negative":
            return "Cash Burn"

        if cfo == "Negative" and cfi == "Positive":
            return "Asset Sale / Funding Dependence"

        return "Mixed / Neutral"

    df["capital_allocation_pattern"] = df.apply(
        capital_pattern,
        axis=1,
    )

    # ---------------------------------------------------------
    # 11. NEGATIVE FCF FLAG
    # ---------------------------------------------------------

    df["negative_fcf_flag"] = (
        df.groupby("company_id")[
            "free_cash_flow_cr"
        ]
        .transform(
            lambda x: (
                x.rolling(3, min_periods=3)
                .apply(
                    lambda values: int(
                        np.all(values < 0)
                    ),
                    raw=True,
                )
            )
        )
    )

    # ---------------------------------------------------------
    # 12. EDGE CASE LOG
    # ---------------------------------------------------------

    edge_cases = []

    zero_sales = int(
        (df["sales"].fillna(0) == 0).sum()
    )

    negative_equity = int(
        (df["total_equity"].fillna(0) < 0).sum()
    )

    debt_free_count = int(
        (df["borrowings"].fillna(0) <= 0).sum()
    )

    negative_fcf_count = int(
        (df["free_cash_flow_cr"].fillna(0) < 0).sum()
    )

    edge_cases.append(
        f"Rows with zero sales: {zero_sales}"
    )

    edge_cases.append(
        f"Rows with negative equity: {negative_equity}"
    )

    edge_cases.append(
        f"Debt-free rows: {debt_free_count}"
    )

    edge_cases.append(
        f"Rows with negative FCF: {negative_fcf_count}"
    )

    EDGE_LOG.write_text(
        "\n".join(edge_cases),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 13. FINAL OUTPUT
    # ---------------------------------------------------------

    exclude_columns = {
                "sales",
        "opm_percentage",
        "id_bs",
        "year_bs",
        "id_cf",
        "year_cf",
        "id",
        "year",
        "year_normalized",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
        "expenses",
        "operating_profit",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    }

    ratio_columns = [
        column
        for column in df.columns
        if column not in exclude_columns
    ]

    final_df = df[
        ["company_id", "year_normalized"]
        + ratio_columns
    ].copy()

    # Remove accidental duplicate columns
    final_df = final_df.loc[
        :,
        ~final_df.columns.duplicated(),
    ]

    final_df.to_csv(
        RATIO_OUTPUT,
        index=False,
    )

    # ---------------------------------------------------------
    # Capital allocation output
    # ---------------------------------------------------------

    capital_columns = [
        "company_id",
        "year_normalized",
        "cfo",
        "cfi",
        "cff",
        "CFO_sign",
        "CFI_sign",
        "CFF_sign",
        "capital_allocation_pattern",
        "free_cash_flow_cr",
        "negative_fcf_flag",
    ]

    capital_df = df[
        capital_columns
    ].copy()

    capital_df.to_csv(
        CAPITAL_OUTPUT,
        index=False,
    )

    # ---------------------------------------------------------
    # Update SQLite
    # ---------------------------------------------------------

    final_df.to_sql(
        "financial_ratios_calculated",
        connection,
        if_exists="replace",
        index=False,
    )

    connection.close()

    # ---------------------------------------------------------
    # Final message
    # ---------------------------------------------------------

    print()
    print("==============================================")
    print("FINANCIAL RATIO ENGINE COMPLETE")
    print("==============================================")
    print(f"Rows generated: {len(final_df)}")
    print(f"KPIs generated: {len(ratio_columns)}")
    print(f"Saved: {RATIO_OUTPUT}")
    print(f"Saved: {CAPITAL_OUTPUT}")
    print(f"Saved: {EDGE_LOG}")
    print("SQLite table updated: financial_ratios_calculated")
    print("==============================================")


if __name__ == "__main__":
    main()