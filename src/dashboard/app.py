
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Nifty 100 Financial Intelligence",
    page_icon="📊",
    layout="wide",
)

# Locate the project database
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"


# --------------------------------------------------
# DATABASE FUNCTIONS
# --------------------------------------------------

@st.cache_data
def load_data(query, params=()):
    """Read data from the SQLite database."""
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(query, connection, params=params)


# --------------------------------------------------
# DASHBOARD HEADER
# --------------------------------------------------

st.title("📊 Nifty 100 Financial Intelligence")
st.caption(
    "Analyze company performance, financial history, "
    "and key financial indicators."
)

st.divider()


# --------------------------------------------------
# DATABASE CHECK
# --------------------------------------------------

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()

try:
    companies = load_data(
        """
        SELECT id, company_name
        FROM companies
        WHERE company_name IS NOT NULL
        ORDER BY company_name
        """
    )

    if companies.empty:
        st.warning("No companies were found in the database.")
        st.stop()

    # --------------------------------------------------
    # OVERVIEW METRICS
    # --------------------------------------------------

    tables = load_data(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        """
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Companies", f"{len(companies):,}")
    col2.metric("Database tables", f"{len(tables):,}")
    col3.metric("Database status", "Connected")

    st.divider()

    # --------------------------------------------------
    # COMPANY SELECTION
    # --------------------------------------------------

    st.subheader("🏢 Company Analysis")

    selected_company = st.selectbox(
        "Select a company",
        companies["company_name"].tolist(),
    )

    company_row = companies.loc[
        companies["company_name"] == selected_company
    ].iloc[0]

    company_id = company_row["id"]

    st.write(f"**Selected company:** {selected_company}")
    st.write(f"**Company ID:** {company_id}")

    # --------------------------------------------------
    # LOAD PROFIT AND LOSS HISTORY
    # --------------------------------------------------

    financials = load_data(
        """
        SELECT year, sales, net_profit, eps, opm_percentage
        FROM profit_loss
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    )

    if financials.empty:
        st.info(
            "No profit-and-loss records were found "
            "for this company."
        )
        st.stop()

    # Convert numeric columns safely
    numeric_columns = [
        "sales",
        "net_profit",
        "eps",
        "opm_percentage",
    ]

    for column in numeric_columns:
        financials[column] = pd.to_numeric(
            financials[column],
            errors="coerce",
        )

    # Use the last available record as the latest record
    latest = financials.iloc[-1]

    # --------------------------------------------------
    # KEY FINANCIAL INDICATORS
    # --------------------------------------------------

    st.subheader("💰 Latest Financial Performance")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Sales",
        (
            f"{latest['sales']:,.2f}"
            if pd.notna(latest["sales"])
            else "N/A"
        ),
    )

    col2.metric(
        "Net Profit",
        (
            f"{latest['net_profit']:,.2f}"
            if pd.notna(latest["net_profit"])
            else "N/A"
        ),
    )

    col3.metric(
        "EPS",
        (
            f"{latest['eps']:,.2f}"
            if pd.notna(latest["eps"])
            else "N/A"
        ),
    )

    col4.metric(
        "Operating Profit Margin",
        (
            f"{latest['opm_percentage']:.2f}%"
            if pd.notna(latest["opm_percentage"])
            else "N/A"
        ),
    )

    st.caption(
        f"Figures correspond to the latest available record: "
        f"{latest['year']}."
    )

    st.divider()

    # --------------------------------------------------
    # FINANCIAL CHARTS
    # --------------------------------------------------

    st.subheader("📈 Financial Trends")

    chart_data = financials.copy()
    chart_data["year"] = chart_data["year"].astype(str)

    chart_data = chart_data.set_index("year")[
        ["sales", "net_profit"]
    ]

    st.line_chart(
        chart_data,
        x_label="Financial year",
        y_label="Amount",
    )

    st.subheader("Operating Profit Margin")

    margin_data = financials[
        ["year", "opm_percentage"]
    ].copy()

    margin_data["year"] = margin_data["year"].astype(str)
    margin_data = margin_data.set_index("year")

    st.bar_chart(
        margin_data,
        y="opm_percentage",
        x_label="Financial year",
        y_label="Operating profit margin (%)",
    )

    st.divider()

    # --------------------------------------------------
    # FINANCIAL HISTORY TABLE
    # --------------------------------------------------

    st.subheader("📋 Complete Financial History")

    st.dataframe(
        financials.sort_values(
            "year",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # DOWNLOAD DATA
    # --------------------------------------------------

    csv_data = financials.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Financial History (CSV)",
        data=csv_data,
        file_name="company_financial_history.csv",
        mime="text/csv",
    )

except Exception as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.caption(
        "Check the database connection, table names, "
        "and column names if the problem continues."
    )
