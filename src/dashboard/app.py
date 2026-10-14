
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

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"


# --------------------------------------------------
# DATABASE FUNCTION
# --------------------------------------------------

@st.cache_data
def load_data(query, params=()):
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(query, connection, params=params)


def format_number(value, suffix=""):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.2f}{suffix}"


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("📊 Nifty 100 Financial Intelligence")
st.caption(
    "Company profiles, financial performance, market data "
    "and financial ratios."
)

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
        st.warning("No companies found in the database.")
        st.stop()

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

    company = companies.loc[
        companies["company_name"] == selected_company
    ].iloc[0]

    company_id = company["id"]

    st.write(f"**Company:** {selected_company}")
    st.write(f"**Company ID:** {company_id}")

    # --------------------------------------------------
    # SECTOR DETAILS
    # --------------------------------------------------

    sector = load_data(
        """
        SELECT broad_sector, sub_sector,
               index_weight_pct, market_cap_category
        FROM sectors
        WHERE company_id = ?
        LIMIT 1
        """,
        (company_id,),
    )

    st.subheader("🏷️ Company Classification")

    if sector.empty:
        st.info("Sector information is not available.")
    else:
        details = sector.iloc[0]
        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Broad Sector",
            str(details["broad_sector"])
            if pd.notna(details["broad_sector"]) else "N/A",
        )
        c2.metric(
            "Sub-sector",
            str(details["sub_sector"])
            if pd.notna(details["sub_sector"]) else "N/A",
        )
        c3.metric(
            "Index Weight",
            format_number(details["index_weight_pct"], "%"),
        )
        c4.metric(
            "Market Cap Category",
            str(details["market_cap_category"])
            if pd.notna(details["market_cap_category"]) else "N/A",
        )

    # --------------------------------------------------
    # PROFIT AND LOSS
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

    st.divider()
    st.subheader("💰 Profit and Loss Performance")

    if financials.empty:
        st.info("No profit-and-loss records are available.")
    else:
        for column in [
            "sales", "net_profit", "eps", "opm_percentage"
        ]:
            financials[column] = pd.to_numeric(
                financials[column], errors="coerce"
            )

        latest = financials.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sales", format_number(latest["sales"]))
        c2.metric("Net Profit", format_number(latest["net_profit"]))
        c3.metric("EPS", format_number(latest["eps"]))
        c4.metric(
            "Operating Profit Margin",
            format_number(latest["opm_percentage"], "%"),
        )

        st.caption(f"Latest available financial year: {latest['year']}")

        chart_data = financials.copy()
        chart_data["year"] = chart_data["year"].astype(str)
        chart_data = chart_data.set_index("year")[["sales", "net_profit"]]

        st.line_chart(chart_data)

        with st.expander("View complete profit-and-loss history"):
            st.dataframe(
                financials.sort_values("year", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

        st.download_button(
            "⬇️ Download Financial History (CSV)",
            data=financials.to_csv(index=False).encode("utf-8"),
            file_name="company_financial_history.csv",
            mime="text/csv",
        )

    # --------------------------------------------------
    # MARKET CAPITALIZATION
    # --------------------------------------------------

    st.divider()
    st.subheader("📈 Market Data")

    market_data = load_data(
        """
        SELECT year, market_cap_crore, enterprise_value_crore,
               pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year_normalized, year
        """,
        (company_id,),
    )

    if market_data.empty:
        st.info("No market data is available for this company.")
    else:
        for column in market_data.columns:
            if column != "year":
                market_data[column] = pd.to_numeric(
                    market_data[column], errors="coerce"
                )

        latest_market = market_data.iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Market Cap (₹ crore)",
            format_number(latest_market["market_cap_crore"]),
        )
        c2.metric(
            "P/E Ratio",
            format_number(latest_market["pe_ratio"]),
        )
        c3.metric(
            "P/B Ratio",
            format_number(latest_market["pb_ratio"]),
        )

        with st.expander("View complete market data"):
            st.dataframe(
                market_data.sort_values("year", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------
    # CALCULATED FINANCIAL RATIOS
    # --------------------------------------------------

    st.divider()
    st.subheader("🧮 Financial Ratios")

    ratios = load_data(
        """
        SELECT year_normalized,
               net_profit_margin_pct,
               operating_profit_margin_pct,
               return_on_equity_pct,
               return_on_assets_pct,
               return_on_capital_employed_pct,
               debt_to_equity,
               debt_to_assets_pct,
               interest_coverage,
               free_cash_flow_cr,
               revenue_growth_pct,
               profit_growth_pct
        FROM financial_ratios_calculated
        WHERE company_id = ?
        ORDER BY year_normalized
        """,
        (company_id,),
    )

    if ratios.empty:
        st.info("No calculated financial ratios are available.")
    else:
        ratios = ratios.copy()

        for column in ratios.columns:
            if column != "year_normalized":
                ratios[column] = pd.to_numeric(
                    ratios[column], errors="coerce"
                )

        latest_ratio = ratios.iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Net Profit Margin",
            format_number(latest_ratio["net_profit_margin_pct"], "%"),
        )
        c2.metric(
            "Return on Equity",
            format_number(latest_ratio["return_on_equity_pct"], "%"),
        )
        c3.metric(
            "Debt to Equity",
            format_number(latest_ratio["debt_to_equity"]),
        )

        c4, c5, c6 = st.columns(3)
        c4.metric(
            "Return on Assets",
            format_number(latest_ratio["return_on_assets_pct"], "%"),
        )
        c5.metric(
            "Interest Coverage",
            format_number(latest_ratio["interest_coverage"]),
        )
        c6.metric(
            "Free Cash Flow (₹ crore)",
            format_number(latest_ratio["free_cash_flow_cr"]),
        )

        st.subheader("Ratio Trends")

        available_metrics = [
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "return_on_equity_pct",
            "return_on_assets_pct",
            "revenue_growth_pct",
            "profit_growth_pct",
        ]

        selected_metrics = st.multiselect(
            "Choose ratios to compare over time",
            available_metrics,
            default=[
                "net_profit_margin_pct",
                "return_on_equity_pct",
            ],
        )

        if selected_metrics:
            ratio_chart = ratios.set_index("year_normalized")[
                selected_metrics
            ]
            st.line_chart(ratio_chart)

        with st.expander("View all calculated ratios"):
            st.dataframe(
                ratios.sort_values(
                    "year_normalized", ascending=False
                ),
                use_container_width=True,
                hide_index=True,
            )

except Exception as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.exception(error)
