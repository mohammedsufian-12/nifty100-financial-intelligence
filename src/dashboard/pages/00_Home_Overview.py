import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"


def show_home_overview():
    st.title("Nifty 100 Financial Overview")
    st.caption("A quick overview of company performance and market data.")

    if not DB_PATH.exists():
        st.error("Database not found.")
        return

    with sqlite3.connect(DB_PATH) as connection:
        roe = pd.read_sql_query("""
            SELECT f.return_on_equity_pct
            FROM financial_ratios_calculated f
            JOIN (
                SELECT company_id, MAX(year_normalized) AS latest_year
                FROM financial_ratios_calculated
                GROUP BY company_id
            ) latest
            ON f.company_id = latest.company_id
            AND f.year_normalized = latest.latest_year
        """, connection)

        pe = pd.read_sql_query("""
            SELECT m.pe_ratio
            FROM market_cap m
            JOIN (
                SELECT company_id, MAX(year_normalized) AS latest_year
                FROM market_cap
                GROUP BY company_id
            ) latest
            ON m.company_id = latest.company_id
            AND m.year_normalized = latest.latest_year
        """, connection)

        sectors = pd.read_sql_query("""
            SELECT broad_sector, COUNT(*) AS company_count
            FROM sectors
            WHERE broad_sector IS NOT NULL
            GROUP BY broad_sector
            ORDER BY company_count DESC
        """, connection)

    roe["return_on_equity_pct"] = pd.to_numeric(
        roe["return_on_equity_pct"], errors="coerce"
    )
    pe["pe_ratio"] = pd.to_numeric(pe["pe_ratio"], errors="coerce")

    average_roe = roe["return_on_equity_pct"].mean()
    median_pe = pe.loc[pe["pe_ratio"] > 0, "pe_ratio"].median()

    col1, col2 = st.columns(2)
    col1.metric(
        "Average ROE",
        f"{average_roe:.2f}%" if pd.notna(average_roe) else "N/A",
    )
    col2.metric(
        "Median P/E",
        f"{median_pe:.2f}" if pd.notna(median_pe) else "N/A",
    )

    st.subheader("Sector Distribution")
    if sectors.empty:
        st.info("Sector information is unavailable.")
    else:
        st.bar_chart(
            sectors.set_index("broad_sector")["company_count"]
        )

    st.subheader("Market Health Summary")
    if pd.isna(average_roe) or pd.isna(median_pe):
        st.info("Not enough data to summarize market health.")
    else:
        st.write(
            f"The latest available data shows an average ROE of "
            f"{average_roe:.2f}% and a median positive P/E of "
            f"{median_pe:.2f}. These figures describe profitability "
            f"and valuation; they do not alone determine overall market health."
        )


if __name__ == "__main__":
    show_home_overview()