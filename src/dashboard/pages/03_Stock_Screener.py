
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Stock Screener | Nifty 100",
    page_icon="🔎",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@st.cache_data
def load_screening_data():
    query = """
        SELECT
            c.company_name,
            r.company_id,
            r.year_normalized,
            r.return_on_equity_pct,
            r.operating_profit_margin_pct,
            r.net_profit_margin_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.revenue_growth_pct,
            r.profit_growth_pct
        FROM financial_ratios_calculated r
        LEFT JOIN companies c ON c.id = r.company_id
        WHERE r.year_normalized IS NOT NULL
        ORDER BY r.year_normalized DESC
    """

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


st.title("🔎 Nifty 100 Stock Screener")
st.caption("Filter companies using profitability, growth, and debt metrics.")

try:
    data = load_screening_data()

    if data.empty:
        st.warning("No calculated financial ratios are available.")
        st.stop()

    data["year_normalized"] = pd.to_numeric(
        data["year_normalized"], errors="coerce"
    )

    # Keep the latest available financial year for each company.
    data = data.dropna(subset=["year_normalized"])
    data = data.sort_values("year_normalized", ascending=False)
    data = data.drop_duplicates(subset=["company_id"], keep="first")

    years = sorted(data["year_normalized"].astype(int).unique(), reverse=True)
    selected_year = st.selectbox("Financial year", years)

    year_data = load_screening_data()
    year_data["year_normalized"] = pd.to_numeric(
        year_data["year_normalized"], errors="coerce"
    )
    year_data = year_data[year_data["year_normalized"] == selected_year]

    st.subheader("Set Your Screening Conditions")

    col1, col2 = st.columns(2)

    with col1:
        min_roe = st.slider(
            "Minimum Return on Equity (%)", 0, 50, 10
        )
        min_opm = st.slider(
            "Minimum Operating Profit Margin (%)", 0, 50, 10
        )
        min_growth = st.slider(
            "Minimum Profit Growth (%)", -50, 100, 0
        )

    with col2:
        max_debt = st.slider(
            "Maximum Debt-to-Equity", 0.0, 5.0, 1.0, step=0.1
        )
        min_coverage = st.slider(
            "Minimum Interest Coverage", 0.0, 20.0, 2.0, step=0.5
        )

    filtered = year_data.copy()

    filtered = filtered[
        (filtered["return_on_equity_pct"] >= min_roe)
        & (filtered["operating_profit_margin_pct"] >= min_opm)
        & (filtered["profit_growth_pct"] >= min_growth)
        & (filtered["debt_to_equity"] <= max_debt)
        & (filtered["interest_coverage"] >= min_coverage)
    ]

    st.divider()

    col1, col2 = st.columns(2)
    col1.metric("Companies matching conditions", len(filtered))
    col2.metric("Financial year", int(selected_year))

    st.subheader("Screening Results")

    if filtered.empty:
        st.info("No companies match all these conditions. Try relaxing a filter.")
    else:
        display_columns = [
            "company_name",
            "year_normalized",
            "return_on_equity_pct",
            "operating_profit_margin_pct",
            "profit_growth_pct",
            "debt_to_equity",
            "interest_coverage",
        ]

        results = filtered[display_columns].sort_values(
            "return_on_equity_pct", ascending=False
        )

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download screening results (CSV)",
            results.to_csv(index=False).encode("utf-8"),
            file_name="nifty100_screening_results.csv",
            mime="text/csv",
        )

        st.caption(
            "These filters are for financial research and do not constitute "
            "investment advice. Missing financial values may exclude companies."
        )

except Exception as error:
    st.error("Unable to load the Stock Screener.")
    st.exception(error)
