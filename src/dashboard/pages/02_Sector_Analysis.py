
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Sector Analysis | Nifty 100",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@st.cache_data
def load_data(query):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


st.title("📊 Sector Analysis")
st.caption("Explore sector distribution and company-level financial data.")

try:
    sectors = load_data("""
        SELECT
            s.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM sectors s
        LEFT JOIN companies c ON c.id = s.company_id
        ORDER BY s.broad_sector, c.company_name
    """)

    if sectors.empty:
        st.warning("No sector data found in the database.")
        st.stop()

    sectors["broad_sector"] = sectors["broad_sector"].fillna("Unknown")
    sectors["sub_sector"] = sectors["sub_sector"].fillna("Unknown")

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Companies with sector records", len(sectors))
    col2.metric("Broad sectors", sectors["broad_sector"].nunique())
    col3.metric("Sub-sectors", sectors["sub_sector"].nunique())

    st.divider()

    # Sector distribution
    st.subheader("Companies by Sector")
    sector_counts = (
        sectors.groupby("broad_sector")
        .size()
        .sort_values(ascending=False)
        .rename("Companies")
    )

    st.bar_chart(sector_counts)

    st.divider()

    # Sector selector
    st.subheader("Explore a Sector")
    sector_options = sorted(sectors["broad_sector"].unique())
    selected_sector = st.selectbox("Choose a sector", sector_options)

    filtered = sectors[
        sectors["broad_sector"] == selected_sector
    ].copy()

    st.write(f"**{selected_sector}** — {len(filtered)} company records")

    if "index_weight_pct" in filtered.columns:
        weights = pd.to_numeric(
            filtered["index_weight_pct"], errors="coerce"
        )
        filtered["index_weight_pct"] = weights

    display_columns = [
        "company_name",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    # Sub-sector distribution
    st.subheader("Sub-sector Distribution")
    sub_counts = (
        filtered.groupby("sub_sector")
        .size()
        .sort_values(ascending=False)
        .rename("Companies")
    )
    st.bar_chart(sub_counts)

    st.download_button(
        "Download sector companies (CSV)",
        filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="sector_analysis.csv",
        mime="text/csv",
    )

except Exception as error:
    st.error("Unable to load sector analysis.")
    st.exception(error)
