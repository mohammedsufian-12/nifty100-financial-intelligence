
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Peer Comparison | Nifty 100",
    page_icon="🤝",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@st.cache_data
def load_data(query):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


st.title("🤝 Peer Comparison")
st.caption("Compare companies with other members of their peer groups.")

try:
    peer_groups = load_data("""
        SELECT
            pg.peer_group_name,
            pg.company_id,
            pg.is_benchmark,
            c.company_name
        FROM peer_groups pg
        LEFT JOIN companies c ON c.id = pg.company_id
        ORDER BY pg.peer_group_name, c.company_name
    """)

    if peer_groups.empty:
        st.warning("No peer-group data found.")
        st.stop()

    groups = sorted(peer_groups["peer_group_name"].dropna().unique())

    if not groups:
        st.warning("No peer groups are available.")
        st.stop()

    selected_group = st.selectbox("Select a peer group", groups)

    group_data = peer_groups[
        peer_groups["peer_group_name"] == selected_group
    ].copy()

    st.subheader(selected_group)
    st.metric("Companies in this group", len(group_data))

    st.dataframe(
        group_data[["company_name", "is_benchmark"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Compare Financial Ratios")

    ratio_data = load_data("""
        SELECT
            c.company_name,
            r.year_normalized,
            r.return_on_equity_pct,
            r.operating_profit_margin_pct,
            r.net_profit_margin_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.revenue_growth_pct,
            r.profit_growth_pct
        FROM financial_ratios_calculated r
        JOIN companies c ON c.id = r.company_id
        WHERE r.year_normalized IS NOT NULL
    """)

    group_ids = group_data["company_id"].tolist()

    # Convert IDs to strings to handle text-based company identifiers.
    ratio_data["company_id"] = ratio_data.get(
        "company_id", pd.Series(dtype=str)
    )

    # Select only companies belonging to this peer group.
    company_names = group_data["company_name"].dropna().tolist()
    comparison = ratio_data[
        ratio_data["company_name"].isin(company_names)
    ].copy()

    if comparison.empty:
        st.info("No calculated ratio records were found for this peer group.")
    else:
        comparison["year_normalized"] = pd.to_numeric(
            comparison["year_normalized"], errors="coerce"
        )

        latest = (
            comparison.dropna(subset=["year_normalized"])
            .sort_values("year_normalized", ascending=False)
            .drop_duplicates(subset=["company_name"])
        )

        metric_options = {
            "Return on Equity (%)": "return_on_equity_pct",
            "Operating Profit Margin (%)": "operating_profit_margin_pct",
            "Net Profit Margin (%)": "net_profit_margin_pct",
            "Debt-to-Equity": "debt_to_equity",
            "Interest Coverage": "interest_coverage",
            "Revenue Growth (%)": "revenue_growth_pct",
            "Profit Growth (%)": "profit_growth_pct",
        }

        selected_metric = st.selectbox(
            "Choose a metric to compare",
            list(metric_options.keys()),
        )

        metric_column = metric_options[selected_metric]

        chart_data = latest.set_index("company_name")[[metric_column]]
        st.bar_chart(chart_data)

        st.dataframe(
            latest[
                ["company_name", "year_normalized", metric_column]
            ].sort_values(metric_column, ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download peer comparison (CSV)",
            latest.to_csv(index=False).encode("utf-8"),
            file_name="peer_comparison.csv",
            mime="text/csv",
        )

except Exception as error:
    st.error("Unable to load peer comparison.")
    st.exception(error)
