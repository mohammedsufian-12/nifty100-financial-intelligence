
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Company Analysis | Nifty 100",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@st.cache_data
def load_data(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


def show_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.2f}"


st.title("🏢 Company Analysis")
st.caption("Financial performance and historical data for Nifty 100 companies.")

try:
    companies = load_data(
        "SELECT id, company_name FROM companies ORDER BY company_name"
    )

    if companies.empty:
        st.warning("No company data found.")
        st.stop()

    selected_company = st.selectbox(
        "Select a company",
        companies["company_name"].tolist(),
    )

    company_id = companies.loc[
    companies["company_name"] == selected_company, "id"
].iloc[0]
    

    company_info = load_data(
        """
        SELECT c.company_name, c.about_company, c.website,
               s.broad_sector, s.sub_sector,
               s.index_weight_pct, s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE c.id = ?
        LIMIT 1
        """,
        (company_id,),
    )

    if not company_info.empty:
        info = company_info.iloc[0]

        st.subheader(selected_company)

        description = info.get("about_company")
        if pd.notna(description) and description:
            st.write(description)

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Sector",
            info.get("broad_sector")
            if pd.notna(info.get("broad_sector"))
            else "N/A",
        )
        col2.metric(
            "Index Weight",
            f"{show_number(info.get('index_weight_pct'))}%"
            if pd.notna(info.get("index_weight_pct"))
            else "N/A",
        )
        col3.metric(
            "Market Cap Category",
            info.get("market_cap_category")
            if pd.notna(info.get("market_cap_category"))
            else "N/A",
        )

        website = info.get("website")
        if pd.notna(website) and website:
            st.markdown(f"[Company website]({website})")

    st.divider()

    financials = load_data(
        """
        SELECT year_normalized, sales, net_profit, eps,
               opm_percentage
        FROM profit_loss
        WHERE company_id = ?
          AND year_normalized IS NOT NULL
        ORDER BY year_normalized
        """,
        (company_id,),
    )

    st.subheader("Profit and Loss History")

    if not financials.empty:
        latest = financials.iloc[-1]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latest Sales", show_number(latest["sales"]))
        col2.metric("Latest Net Profit", show_number(latest["net_profit"]))
        col3.metric("Latest EPS", show_number(latest["eps"]))
        col4.metric("Operating Profit Margin", 
                    f"{show_number(latest['opm_percentage'])}%")

        chart_data = financials.set_index("year_normalized")[
            ["sales", "net_profit"]
        ]
        st.line_chart(chart_data)

        with st.expander("View complete financial history"):
            st.dataframe(financials, use_container_width=True)

        st.download_button(
            "Download financial history (CSV)",
            financials.to_csv(index=False).encode("utf-8"),
            file_name="company_financial_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No normalized profit-and-loss history is available.")

    st.divider()

    ratios = load_data(
        """
        SELECT *
        FROM financial_ratios_calculated
        WHERE company_id = ?
        ORDER BY year_normalized
        """,
        (company_id,),
    )

    st.subheader("Calculated Financial Ratios")

    if not ratios.empty:
        st.dataframe(ratios, use_container_width=True)

        numeric_columns = [
            col for col in ratios.columns
            if col.endswith("_pct")
            or col in ("debt_to_equity", "interest_coverage")
        ]

        if numeric_columns:
            selected_ratios = st.multiselect(
                "Choose ratios to compare over time",
                numeric_columns,
                default=numeric_columns[:3],
            )

            if selected_ratios and "year_normalized" in ratios.columns:
                st.line_chart(
                    ratios.set_index("year_normalized")[selected_ratios]
                )
    else:
        st.info("No calculated ratios found for this company.")

except Exception as error:
    st.error("Unable to load company analysis.")
    st.exception(error)
