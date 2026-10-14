
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Capital Allocation | Nifty 100",
    page_icon="💰",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

@st.cache_data
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        query = """
            SELECT
                c.id AS company_id,
                c.company_name,
                cf.year_normalized,
                cf.operating_activity,
                cf.investing_activity,
                cf.financing_activity
            FROM companies AS c
            INNER JOIN cash_flow AS cf
                ON cf.company_id = c.id
            WHERE cf.year_normalized IS NOT NULL
            ORDER BY c.company_name, cf.year_normalized
        """
        return pd.read_sql_query(query, conn)


# --------------------------------------------------
# CAPITAL ALLOCATION CLASSIFICATION
# --------------------------------------------------

def classify_capital(row):
    operating = row["operating_activity"]
    investing = row["investing_activity"]
    financing = row["financing_activity"]

    if pd.isna(operating) or pd.isna(investing) or pd.isna(financing):
        return "Insufficient Data"

    if operating > 0 and investing < 0 and financing < 0:
        return "Self-Funded Growth"

    if operating > 0 and investing < 0 and financing > 0:
        return "Growth with External Funding"

    if operating > 0 and investing > 0 and financing < 0:
        return "Cash Generation / Debt Repayment"

    if operating > 0 and investing > 0 and financing > 0:
        return "Strong Cash Inflows"

    if operating < 0 and investing < 0 and financing > 0:
        return "Externally Funded Investment"

    if operating < 0 and investing > 0 and financing > 0:
        return "Cash-Raising / Operating Pressure"

    if operating < 0 and investing > 0 and financing < 0:
        return "Cash Contraction"

    if operating < 0 and investing < 0 and financing < 0:
        return "Cash Burn"

    return "Mixed / Neutral Pattern"


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("💰 Capital Allocation Map")
st.caption(
    "Explore company cash-flow patterns using operating, "
    "investing, and financing activities."
)

st.info(
    "These categories are rule-based interpretations of cash-flow signs. "
    "They are analytical indicators, not investment recommendations."
)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

try:
    data = load_data()

    if data.empty:
        st.warning("No cash-flow data was found in the database.")
        st.stop()

    numeric_columns = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data["year_normalized"] = pd.to_numeric(
        data["year_normalized"],
        errors="coerce",
    )

    data = data.dropna(subset=["year_normalized"])
    data["year_normalized"] = data["year_normalized"].astype(int)

    # Use the latest available cash-flow year for each company.
    latest_data = (
        data.sort_values("year_normalized")
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest_data["capital_pattern"] = latest_data.apply(
        classify_capital,
        axis=1,
    )

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    st.subheader("Filters")

    col1, col2 = st.columns(2)

    with col1:
        available_years = sorted(
            data["year_normalized"].unique().tolist(),
            reverse=True,
        )

        selected_year = st.selectbox(
            "Select financial year",
            available_years,
        )

    year_data = data[
        data["year_normalized"] == selected_year
    ].copy()

    year_data["capital_pattern"] = year_data.apply(
        classify_capital,
        axis=1,
    )

    with col2:
        patterns = sorted(
            year_data["capital_pattern"].unique().tolist()
        )

        selected_patterns = st.multiselect(
            "Capital allocation pattern",
            patterns,
            default=patterns,
        )

    filtered_data = year_data[
        year_data["capital_pattern"].isin(selected_patterns)
    ].copy()

    st.divider()

    # --------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------

    st.subheader("Capital Allocation Summary")

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric(
        "Companies in selected year",
        f"{len(year_data['company_id'].unique()):,}",
    )

    metric2.metric(
        "Self-funded growth",
        int(
            (
                year_data["capital_pattern"]
                == "Self-Funded Growth"
            ).sum()
        ),
    )

    metric3.metric(
        "Cash burn",
        int(
            (
                year_data["capital_pattern"]
                == "Cash Burn"
            ).sum()
        ),
    )

    # --------------------------------------------------
    # TREEMAP
    # --------------------------------------------------

    st.subheader("Company Capital Allocation Treemap")

    if filtered_data.empty:
        st.info("No companies match the selected filters.")
    else:
        treemap_data = filtered_data.copy()

        treemap_data["company_size"] = 1

        fig = px.treemap(
            treemap_data,
            path=["capital_pattern", "company_name"],
            values="company_size",
            color="capital_pattern",
            hover_data={
                "operating_activity": ":.2f",
                "investing_activity": ":.2f",
                "financing_activity": ":.2f",
                "year_normalized": True,
                "company_size": False,
            },
            title=f"Capital Allocation Patterns — {selected_year}",
        )

        fig.update_layout(
            margin=dict(t=50, l=10, r=10, b=10),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # --------------------------------------------------
    # PATTERN DISTRIBUTION
    # --------------------------------------------------

    st.subheader("Company Count by Pattern")

    if not filtered_data.empty:
        pattern_counts = (
            filtered_data["capital_pattern"]
            .value_counts()
            .rename_axis("Capital Pattern")
            .reset_index(name="Companies")
        )

        fig = px.bar(
            pattern_counts,
            x="Capital Pattern",
            y="Companies",
            color="Capital Pattern",
            title="Companies in Each Capital Allocation Pattern",
        )

        fig.update_layout(
            showlegend=False,
            xaxis_tickangle=-30,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # --------------------------------------------------
    # COMPANY TABLE
    # --------------------------------------------------

    st.subheader("Company Details")

    display_columns = [
        "company_name",
        "year_normalized",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "capital_pattern",
    ]

    st.dataframe(
        filtered_data[display_columns].sort_values(
            "company_name"
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # CSV DOWNLOAD
    # --------------------------------------------------

    csv_data = filtered_data[display_columns].to_csv(
        index=False
    )

    st.download_button(
        label="Download Capital Allocation CSV",
        data=csv_data,
        file_name=f"capital_allocation_{selected_year}.csv",
        mime="text/csv",
    )

except Exception as error:
    st.error("Unable to load the Capital Allocation Map.")
    st.exception(error)
