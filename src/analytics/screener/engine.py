from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[3]

RATIO_FILE = BASE_DIR / "data" / "processed" / "financial_ratios_calculated.csv"
CONFIG_FILE = BASE_DIR / "config" / "screener_config.yaml"
DB_FILE = BASE_DIR / "nifty100.db"

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_XLSX = OUTPUT_DIR / "screener_output.xlsx"
OUTPUT_CSV = OUTPUT_DIR / "screener_output.csv"


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Column aliases
# ---------------------------------------------------------------------

COLUMN_ALIASES = { 
    "dividend_payout_pct": "dividend_payout_ratio_pct",
    "revenue_cagr_3yr": "revenue_cagr_3y_pct",
    "revenue_cagr_5yr": "revenue_cagr_5y_pct",
    "revenue_cagr_10yr": "revenue_cagr_10y_pct",
    "pat_cagr_3yr": "pat_cagr_3y_pct",
    "pat_cagr_5yr": "pat_cagr_5y_pct",
    "pat_cagr_10yr": "pat_cagr_10y_pct",
    "eps_cagr_3yr": "eps_cagr_3y_pct",
    "eps_cagr_5yr": "eps_cagr_5y_pct",
    "eps_cagr_10yr": "eps_cagr_10y_pct",
    "fcf_cagr_5yr": "fcf_cagr_5y_pct",
    "fcf_cagr_10yr": "fcf_cagr_10y_pct",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def load_config() -> dict[str, Any]:
    """Load screener configuration from YAML."""
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def normalize_text(value: Any) -> str:
    """Normalize text for column matching."""
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """Find the first matching column from candidate names."""
    normalized = {
        normalize_text(column): column
        for column in df.columns
    }

    for candidate in candidates:
        key = normalize_text(candidate)
        if key in normalized:
            return normalized[key]

    return None


def rename_if_available(
    df: pd.DataFrame,
    source_names: list[str],
    target_name: str,
) -> pd.DataFrame:
    """Rename a column when one of the source names exists."""
    if target_name in df.columns:
        return df

    source = find_column(df, source_names)

    if source and source != target_name:
        df = df.rename(columns={source: target_name})

    return df


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------


def load_ratio_data() -> pd.DataFrame:
    """Load calculated financial ratios."""
    if not RATIO_FILE.exists():
        raise FileNotFoundError(
            f"Ratio file not found: {RATIO_FILE}"
        )

    df = pd.read_csv(RATIO_FILE)

    logger.info(
        "Loaded ratio data: %d rows, %d columns",
        len(df),
        len(df.columns),
    )

    return df


def load_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> pd.DataFrame:
    """Load a SQLite table."""
    try:
        return pd.read_sql_query(
            f"SELECT * FROM {table_name}",
            connection,
        )
    except Exception as exc:
        logger.warning(
            "Could not load table %s: %s",
            table_name,
            exc,
        )
        return pd.DataFrame()


def prepare_market_data(
    ratio_df: pd.DataFrame,
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Merge latest market data required by the screener."""
    market_df = load_table(connection, "market_cap")

    if market_df.empty:
        logger.warning("market_cap table is empty.")
        return ratio_df

    company_col = find_column(
        market_df,
        ["company_id", "id", "company"],
    )

    if company_col is None:
        logger.warning("No company identifier found in market_cap.")
        return ratio_df

    if company_col != "company_id":
        market_df = market_df.rename(
            columns={company_col: "company_id"}
        )

    year_col = find_column(
        market_df,
        ["year_normalized", "year", "date"],
    )

    if year_col:
        market_df["market_year"] = pd.to_numeric(
            market_df[year_col],
            errors="coerce",
        )
        market_df = market_df.sort_values("market_year")

    market_df = market_df.drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    for target, candidates in {
        "pe_ratio": ["pe_ratio", "pe", "p_e", "p/e"],
        "pb_ratio": ["pb_ratio", "pb", "p_b", "p/b"],
        "dividend_yield_pct": [
            "dividend_yield_pct",
            "dividend_yield",
            "div_yield",
            "dividend_yield_percentage",
        ],
    }.items():
        market_df = rename_if_available(
            market_df,
            candidates,
            target,
        )

    market_columns = [
        "company_id",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
    ]

    available = [
        column
        for column in market_columns
        if column in market_df.columns
    ]

    if "company_id" not in available:
        return ratio_df

    return ratio_df.merge(
        market_df[available],
        on="company_id",
        how="left",
        suffixes=("", "_market"),
    )


def prepare_company_data(
    df: pd.DataFrame,
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Add company names and sector information."""
    companies = load_table(connection, "companies")

    if not companies.empty:
        company_col = find_column(
            companies,
            ["company_id", "id"],
        )

        name_col = find_column(
            companies,
            ["company_name", "name", "company"],
        )

        if company_col and name_col:
            companies = companies.rename(
                columns={
                    company_col: "company_id",
                    name_col: "company_name",
                }
            )

            companies = companies[
                ["company_id", "company_name"]
            ].drop_duplicates("company_id")

            df = df.merge(
                companies,
                on="company_id",
                how="left",
            )

    sectors = load_table(connection, "sectors")

    if not sectors.empty:
        sector_id = find_column(
            sectors,
            ["company_id", "id"],
        )

        sector_col = find_column(
            sectors,
            ["broad_sector", "sector"],
        )

        if sector_id and sector_col:
            sectors = sectors.rename(
                columns={
                    sector_id: "company_id",
                    sector_col: "broad_sector",
                }
            )

            sectors = sectors[
                ["company_id", "broad_sector"]
            ].drop_duplicates("company_id")

            df = df.merge(
                sectors,
                on="company_id",
                how="left",
            )

    return df


def prepare_revenue_data(
    df: pd.DataFrame,
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Add latest revenue information from profit and loss data."""
    profit_loss = load_table(connection, "profit_loss")

    if profit_loss.empty:
        return df

    company_col = find_column(
        profit_loss,
        ["company_id", "id"],
    )

    year_col = find_column(
        profit_loss,
        ["year_normalized", "year"],
    )

    revenue_col = find_column(
        profit_loss,
        ["revenue_cr", "revenue", "sales"],
    )

    if not company_col or not year_col or not revenue_col:
        logger.warning(
            "Revenue information could not be resolved."
        )
        return df

    profit_loss = profit_loss.rename(
        columns={
            company_col: "company_id",
            year_col: "year_normalized",
            revenue_col: "revenue_cr",
        }
    )

    profit_loss["year_normalized"] = pd.to_numeric(
        profit_loss["year_normalized"],
        errors="coerce",
    )

    profit_loss["revenue_cr"] = pd.to_numeric(
        profit_loss["revenue_cr"],
        errors="coerce",
    )

    profit_loss = profit_loss.sort_values(
        ["company_id", "year_normalized"]
    )

    latest = (
        profit_loss
        .dropna(subset=["year_normalized"])
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    latest = latest[
        ["company_id", "revenue_cr"]
    ]

    if "revenue_cr" not in df.columns:
        df = df.merge(
            latest,
            on="company_id",
            how="left",
        )

    return df


# ---------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------


def add_derived_metrics(
    df: pd.DataFrame,
    full_ratio_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create screener-specific derived metrics."""
    df = df.copy()

    if "free_cash_flow_cr" in df.columns:
        df["free_cash_flow_positive"] = (
            pd.to_numeric(
                df["free_cash_flow_cr"],
                errors="coerce",
            )
            > 0
        )

    if "company_id" in full_ratio_df.columns:
        trend = full_ratio_df.copy()

        if "year_normalized" in trend.columns:
            trend["year_normalized"] = pd.to_numeric(
                trend["year_normalized"],
                errors="coerce",
            )

            trend = trend.sort_values(
                ["company_id", "year_normalized"]
            )

            if "free_cash_flow_cr" in trend.columns:
                trend["previous_fcf"] = (
                    trend.groupby("company_id")[
                        "free_cash_flow_cr"
                    ].shift(1)
                )

                trend["fcf_improving"] = (
                    trend["free_cash_flow_cr"]
                    > trend["previous_fcf"]
                )

            if "debt_to_equity" in trend.columns:
                trend["previous_de"] = (
                    trend.groupby("company_id")[
                        "debt_to_equity"
                    ].shift(1)
                )

                trend["debt_to_equity_declining"] = (
                    trend["debt_to_equity"]
                    < trend["previous_de"]
                )

            trend_columns = [
                "company_id",
                "year_normalized",
                "fcf_improving",
                "debt_to_equity_declining",
            ]

            trend_columns = [
                column
                for column in trend_columns
                if column in trend.columns
            ]

            trend_latest = (
                trend[trend_columns]
                .dropna(subset=["year_normalized"])
                .drop_duplicates(
                    subset=["company_id"],
                    keep="last",
                )
            )

            merge_columns = [
                column
                for column in [
                    "company_id",
                    "fcf_improving",
                    "debt_to_equity_declining",
                ]
                if column in trend_latest.columns
            ]

            if len(merge_columns) > 1:
                df = df.merge(
                    trend_latest[merge_columns],
                    on="company_id",
                    how="left",
                )

    if "fcf_improving" in df.columns:
        df["free_cash_flow_improving"] = (
            df["fcf_improving"]
            .fillna(False)
            .astype(bool)
        )

    if "debt_to_equity_declining" in df.columns:
        df["debt_to_equity_declining"] = (
            df["debt_to_equity_declining"]
            .fillna(False)
            .astype(bool)
        )

    return df


# ---------------------------------------------------------------------
# Latest company records
# ---------------------------------------------------------------------


def get_latest_records(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Keep the latest available financial record per company."""
    if "year_normalized" not in df.columns:
        return df.drop_duplicates(
            subset=["company_id"],
            keep="last",
        )

    df = df.copy()

    df["year_normalized"] = pd.to_numeric(
        df["year_normalized"],
        errors="coerce",
    )

    return (
        df.sort_values(
            ["company_id", "year_normalized"]
        )
        .dropna(subset=["company_id"])
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# Filter engine
# ---------------------------------------------------------------------


def resolve_metric(
    df: pd.DataFrame,
    metric: str,
) -> str | None:
    """Resolve YAML metric names to actual dataframe columns."""
    if metric in df.columns:
        return metric

    alias = COLUMN_ALIASES.get(metric)

    if alias and alias in df.columns:
        return alias

    return find_column(
        df,
        [metric, alias] if alias else [metric],
    )


def apply_filter(
    df: pd.DataFrame,
    metric: str,
    condition: dict[str, Any],
) -> pd.DataFrame:
    """Apply one screener condition."""
    actual_metric = resolve_metric(df, metric)

    if actual_metric is None:
        logger.warning(
            "Metric '%s' not available. Filter skipped.",
            metric,
        )
        return df

    series = df[actual_metric]

    if metric in {
        "free_cash_flow_positive",
        "free_cash_flow_improving",
        "debt_to_equity_declining",
    }:
        series = series.fillna(False).astype(bool)

    else:
        series = pd.to_numeric(
            series,
            errors="coerce",
        )

    result = df.copy()

    for operator, value in condition.items():
        if operator == "min":
            result = result[series >= float(value)]

        elif operator == "max":
            result = result[series <= float(value)]

        elif operator == "equals":
            if isinstance(value, bool):
                result = result[series == value]
            else:
                result = result[
                    np.isclose(
                        series.astype(float),
                        float(value),
                        equal_nan=False,
                    )
                ]

        else:
            logger.warning(
                "Unsupported filter operator '%s'.",
                operator,
            )

        series = result[actual_metric]

        if metric not in {
            "free_cash_flow_positive",
            "free_cash_flow_improving",
            "debt_to_equity_declining",
        }:
            series = pd.to_numeric(
                series,
                errors="coerce",
            )

    return result


def apply_filters(
    df: pd.DataFrame,
    filters: dict[str, Any],
) -> pd.DataFrame:
    """Apply all filters in a preset."""
    result = df.copy()

    for metric, condition in filters.items():

        # D/E is not used as a standard filter for Financials.
        if (
            metric == "debt_to_equity"
            and "broad_sector" in result.columns
        ):
            financial_mask = (
                result["broad_sector"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    "financial|bank|insurance|nbfc",
                    regex=True,
                )
            )

            non_financial = result[~financial_mask]
            financial = result[financial_mask]

            non_financial = apply_filter(
                non_financial,
                metric,
                condition,
            )

            result = pd.concat(
                [non_financial, financial],
                ignore_index=True,
            )

            continue

        result = apply_filter(
            result,
            metric,
            condition,
        )

    return result


# ---------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------


def percentile_score(
    series: pd.Series,
    higher_is_better: bool = True,
) -> pd.Series:
    """Winsorize at P10/P90 and scale to 0-100."""
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    p10 = values.quantile(0.10)
    p90 = values.quantile(0.90)

    if pd.isna(p10) or pd.isna(p90):
        return pd.Series(
            0.0,
            index=series.index,
        )

    if p10 == p90:
        return pd.Series(
            50.0,
            index=series.index,
        )

    clipped = values.clip(
        lower=p10,
        upper=p90,
    )

    if higher_is_better:
        score = (
            (clipped - p10)
            / (p90 - p10)
            * 100
        )
    else:
        score = (
            (p90 - clipped)
            / (p90 - p10)
            * 100
        )

    return score.fillna(0).clip(0, 100)


def debt_score(series: pd.Series) -> pd.Series:
    """Score debt-to-equity using the project thresholds."""
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    conditions = [
        values <= 0,
        values <= 0.5,
        values <= 1,
        values <= 2,
        values > 5,
    ]

    choices = [
        100,
        85,
        70,
        50,
        0,
    ]

    score = np.select(
        conditions,
        choices,
        default=0,
    )

    return pd.Series(
        score,
        index=series.index,
    ).where(
        values.notna(),
        0,
    )


def interest_coverage_score(
    series: pd.Series,
) -> pd.Series:
    """Score interest coverage using project thresholds."""
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    score = np.select(
        [
            values > 10,
            values >= 5,
            values >= 3,
            values >= 1.5,
        ],
        [
            100,
            75,
            50,
            25,
        ],
        default=0,
    )

    return pd.Series(
        score,
        index=series.index,
    ).where(
        values.notna(),
        0,
    )


def calculate_composite_score(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Calculate the composite financial health score."""
    result = df.copy()

    result["score_roe"] = percentile_score(
        result.get(
            "return_on_equity_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_roce"] = percentile_score(
        result.get(
            "return_on_capital_employed_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_npm"] = percentile_score(
        result.get(
            "net_profit_margin_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_fcf_cagr"] = percentile_score(
        result.get(
            "fcf_cagr_5y_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_cfo_pat"] = percentile_score(
        result.get(
            "cfo_to_profit_ratio",
            pd.Series(index=result.index, dtype=float),
        )
    )

    if "free_cash_flow_cr" in result.columns:
        result["score_fcf_positive"] = (
            pd.to_numeric(
                result["free_cash_flow_cr"],
                errors="coerce",
            )
            .gt(0)
            .astype(int)
            * 100
        )
    else:
        result["score_fcf_positive"] = 0

    result["score_revenue_growth"] = percentile_score(
        result.get(
            "revenue_cagr_5y_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_pat_growth"] = percentile_score(
        result.get(
            "pat_cagr_5y_pct",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_debt"] = debt_score(
        result.get(
            "debt_to_equity",
            pd.Series(index=result.index, dtype=float),
        )
    )

    result["score_icr"] = interest_coverage_score(
        result.get(
            "interest_coverage",
            pd.Series(index=result.index, dtype=float),
        )
    )

    weights = {
        "score_roe": 0.15,
        "score_roce": 0.10,
        "score_npm": 0.10,
        "score_fcf_cagr": 0.15,
        "score_cfo_pat": 0.10,
        "score_fcf_positive": 0.05,
        "score_revenue_growth": 0.10,
        "score_pat_growth": 0.10,
        "score_debt": 0.10,
        "score_icr": 0.05,
    }

    result["composite_score"] = 0.0

    for column, weight in weights.items():
        result["composite_score"] += (
            result[column] * weight
        )

    result["composite_score"] = (
        result["composite_score"]
        .clip(0, 100)
        .round(2)
    )

    return result


# ---------------------------------------------------------------------
# Screener execution
# ---------------------------------------------------------------------


def run_preset(
    df: pd.DataFrame,
    preset_name: str,
    preset_config: dict[str, Any],
) -> pd.DataFrame:
    """Run one screener preset."""
    result = apply_filters(
        df,
        preset_config.get("filters", {}),
    )

    ranking_metric = preset_config.get(
        "ranking_metric",
        "composite_score",
    )

    ranking_metric = resolve_metric(
        result,
        ranking_metric,
    )

    if ranking_metric is None:
        ranking_metric = "composite_score"

    result["rank"] = (
        pd.to_numeric(
            result[ranking_metric],
            errors="coerce",
        )
        .rank(
            method="min",
            ascending=False,
        )
    )

    result["preset"] = preset_name

    result = result.sort_values(
        ["rank", "company_id"],
        na_position="last",
    )

    return result


def select_output_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Select useful screener output columns."""
    preferred = [
        "preset",
        "rank",
        "company_id",
        "company_name",
        "broad_sector",
        "year_normalized",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_profit_margin_pct",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow_cr",
        "revenue_cagr_3y_pct",
        "revenue_cagr_5y_pct",
        "pat_cagr_3y_pct",
        "pat_cagr_5y_pct",
        "fcf_cagr_5y_pct",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "revenue_cr",
        "composite_score",
    ]

    columns = [
        column
        for column in preferred
        if column in df.columns
    ]

    return df[columns]


def save_results(
    results: dict[str, pd.DataFrame],
) -> None:
    """Save screener results to CSV and Excel."""
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined = pd.concat(
        results.values(),
        ignore_index=True,
    )

    combined = select_output_columns(combined)

    combined.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    with pd.ExcelWriter(
        OUTPUT_XLSX,
        engine="openpyxl",
    ) as writer:

        summary_rows = []

        for preset_name, result in results.items():
            output = select_output_columns(result)

            sheet_name = preset_name[:31]

            output.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

            summary_rows.append(
                {
                    "preset": preset_name,
                    "matching_companies": len(output),
                }
            )

        pd.DataFrame(summary_rows).to_excel(
            writer,
            sheet_name="summary",
            index=False,
        )

    logger.info(
        "Saved screener CSV: %s",
        OUTPUT_CSV,
    )

    logger.info(
        "Saved screener Excel: %s",
        OUTPUT_XLSX,
    )


def main() -> None:
    """Run the complete screener."""
    config = load_config()

    ratio_df = load_ratio_data()

    connection = sqlite3.connect(DB_FILE)

    try:
        full_ratio_df = ratio_df.copy()

        df = get_latest_records(ratio_df)

        df = prepare_market_data(
            df,
            connection,
        )

        df = prepare_company_data(
            df,
            connection,
        )

        df = prepare_revenue_data(
            df,
            connection,
        )

    finally:
        connection.close()

    df = add_derived_metrics(
        df,
        full_ratio_df,
    )

    df = calculate_composite_score(
        df,
        config,
    )

    presets = config.get(
        "presets",
        {},
    )

    results = {}

    for preset_name, preset_config in presets.items():

        result = run_preset(
            df,
            preset_name,
            preset_config,
        )

        results[preset_name] = result

        logger.info(
            "%s: %d companies matched",
            preset_name,
            len(result),
        )

    save_results(results)

    logger.info("SCREENER COMPLETE")


if __name__ == "__main__":
    main()