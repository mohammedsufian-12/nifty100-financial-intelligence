from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_FILE = BASE_DIR / "nifty100.db"
RATIO_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "financial_ratios_calculated.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "peer_comparison.xlsx"
PERCENTILE_FILE = OUTPUT_DIR / "peer_percentiles.csv"


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


METRICS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_assets_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "revenue_cagr_5y_pct",
    "pat_cagr_5y_pct",
    "earnings_per_share",
    "book_value_per_share_proxy",
    "dividend_payout_ratio_pct",
]



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


def load_peer_groups() -> pd.DataFrame:
    """Load the 11 predefined peer groups."""
    connection = sqlite3.connect(DB_FILE)

    try:
        df = pd.read_sql_query(
            "SELECT * FROM peer_groups",
            connection,
        )
    finally:
        connection.close()

    logger.info(
        "Loaded peer group data: %d rows",
        len(df),
    )

    return df


def find_column(
    df: pd.DataFrame,
    names: list[str],
) -> str | None:
    """Find a matching dataframe column."""
    normalized = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in df.columns
    }

    for name in names:
        key = name.lower().replace(" ", "_")

        if key in normalized:
            return normalized[key]

    return None


def prepare_peer_groups(
    peer_df: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize peer group columns."""
    company_col = find_column(
        peer_df,
        ["company_id", "id"],
    )

    group_col = find_column(
        peer_df,
        [
            "peer_group",
            "peer_group_name",
            "group",
        ],
    )

    if company_col is None:
        raise ValueError(
            "company_id column not found in peer_groups."
        )

    if group_col is None:
        raise ValueError(
            "peer_group column not found in peer_groups."
        )

    peer_df = peer_df.rename(
        columns={
            company_col: "company_id",
            group_col: "peer_group",
        }
    )

    return peer_df[
        ["company_id", "peer_group"]
    ].drop_duplicates()


def get_latest_ratios(
    ratio_df: pd.DataFrame,
) -> pd.DataFrame:
    """Get the latest ratio record for each company."""
    df = ratio_df.copy()

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
    )


def calculate_percentiles(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate percentile rank for each metric within each peer group."""
    records = []

    for peer_group, group in df.groupby(
        "peer_group",
        dropna=False,
    ):
        for metric in METRICS:

            if metric not in group.columns:
                logger.warning(
                    "Metric '%s' not available.",
                    metric,
                )
                continue

            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            )

            valid = values.notna()

            if valid.sum() == 0:
                continue

            percentile = (
                values[valid]
                .rank(
                    method="average",
                    pct=True,
                )
                * 100
            )

            for index in percentile.index:
                records.append(
                    {
                        "company_id": group.loc[
                            index,
                            "company_id",
                        ],
                        "peer_group": peer_group,
                        "metric": metric,
                        "value": values.loc[index],
                        "percentile_rank": round(
                            float(percentile.loc[index]),
                            2,
                        ),
                        "year": group.loc[
                            index,
                            "year_normalized",
                        ],
                    }
                )

    return pd.DataFrame(records)


def create_comparison_tables(
    percentile_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Create one comparison table per peer group."""
    tables = {}

    for peer_group, group in percentile_df.groupby(
        "peer_group",
        dropna=False,
    ):
        pivot = group.pivot_table(
            index="company_id",
            columns="metric",
            values="percentile_rank",
            aggfunc="first",
        )

        pivot = pivot.reset_index()

        tables[str(peer_group)[:31]] = pivot

    return tables


def save_outputs(
    percentile_df: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> None:
    """Save peer percentile and comparison outputs."""
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    percentile_df.to_csv(
        PERCENTILE_FILE,
        index=False,
    )

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl",
    ) as writer:

        summary = (
            percentile_df
            .groupby("peer_group")
            .agg(
                companies=("company_id", "nunique"),
                metrics=("metric", "nunique"),
            )
            .reset_index()
        )

        summary.to_excel(
            writer,
            sheet_name="summary",
            index=False,
        )

        for peer_group, table in tables.items():
            table.to_excel(
                writer,
                sheet_name=peer_group[:31],
                index=False,
            )

    logger.info(
        "Saved percentile data: %s",
        PERCENTILE_FILE,
    )

    logger.info(
        "Saved peer comparison workbook: %s",
        OUTPUT_FILE,
    )


def main() -> None:
    """Run the peer comparison engine."""
    ratio_df = load_ratio_data()

    peer_df = load_peer_groups()

    peer_df = prepare_peer_groups(
        peer_df
    )

    ratio_df = get_latest_ratios(
        ratio_df
    )

    merged = ratio_df.merge(
        peer_df,
        on="company_id",
        how="inner",
    )

    logger.info(
        "Companies matched to peer groups: %d",
        merged["company_id"].nunique(),
    )

    percentile_df = calculate_percentiles(
        merged
    )

    logger.info(
        "Percentile records generated: %d",
        len(percentile_df),
    )

    tables = create_comparison_tables(
        percentile_df
    )

    logger.info(
        "Peer groups generated: %d",
        len(tables),
    )

    save_outputs(
        percentile_df,
        tables,
    )

    logger.info("PEER COMPARISON COMPLETE")


if __name__ == "__main__":
    main()