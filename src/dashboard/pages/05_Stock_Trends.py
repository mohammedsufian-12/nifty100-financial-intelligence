
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Stock Trends | Nifty 100",
    page_icon="📈",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


# --------------------------------------------------
# DATABASE FUNCTION
# --------------------------------------------------

@st.cache_data
def load_data(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


# --------------------------------------------------
# PAGE TITLE
# --------------------------------------------------

st.title("📈 Stock Price & Trend Analysis")
st.caption(
    "Explore historical stock prices and financial growth trends."
)


# --------------------------------------------------
# LOAD COMPANIES
# --------------------------------------------------

try:
    companies = load_data(
        """
        SELECT DISTINCT
            c.id,
            c.company_name
        FROM companies AS c
        INNER JOIN stock_prices AS p
            ON p.company_id = c.id
        ORDER BY c.company_name
        """
    )

    if companies.empty:
        st.warning("No companies with stock price data were found.")
        st.stop()

    selected_company = st.selectbox(
        "Select a company",
        companies["company_name"].tolist(),
    )

    company_id = companies.loc[
        companies["company_name"] == selected_company,
        "id",
    ].iloc[0]

    st.divider()


    # --------------------------------------------------
    # STOCK PRICE HISTORY
    # --------------------------------------------------

    st.subheader("📊 Historical Stock Prices")

    prices = load_data(
        """
        SELECT
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            adjusted_close
        FROM stock_prices
        WHERE company_id = ?
        ORDER BY date
        """,
        (company_id,),
    )

    if prices.empty:
        st.info("No stock price history is available for this company.")
    else:
        prices["date"] = pd.to_datetime(
            prices["date"],
            errors="coerce",
        )

        prices = prices.dropna(subset=["date"])

        for col in [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "adjusted_close",
        ]:
            prices[col] = pd.to_numeric(
                prices[col],
                errors="coerce",
            )

        if not prices.empty:
            latest = prices.iloc[-1]

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Latest closing price",
                (
                    f"₹{latest['close_price']:,.2f}"
                    if pd.notna(latest["close_price"])
                    else "N/A"
                ),
            )

            col2.metric(
                "Highest recorded price",
                (
                    f"₹{prices['high_price'].max():,.2f}"
                    if prices["high_price"].notna().any()
                    else "N/A"
                ),
            )

            col3.metric(
                "Lowest recorded price",
                (
                    f"₹{prices['low_price'].min():,.2f}"
                    if prices["low_price"].notna().any()
                    else "N/A"
                ),
            )

            st.markdown("**Closing Price Trend**")

            close_chart = prices.set_index("date")[
                ["close_price"]
            ].dropna()

            if not close_chart.empty:
                st.line_chart(close_chart)

            if prices["volume"].notna().any():
                st.markdown("**Trading Volume**")
                volume_chart = prices.set_index("date")[
                    ["volume"]
                ].dropna()

                st.bar_chart(volume_chart)

            with st.expander("View stock price data"):
                st.dataframe(
                    prices,
                    use_container_width=True,
                    hide_index=True,
                )

    st.divider()


    # --------------------------------------------------
    # FINANCIAL GROWTH TRENDS
    # --------------------------------------------------

    st.subheader("📈 Financial Growth Trends")

    trends = load_data(
        """
        SELECT *
        FROM financial_ratios_calculated
        WHERE company_id = ?
        ORDER BY year_normalized
        """,
        (company_id,),
    )

    if trends.empty:
        st.info(
            "No financial growth data is available for this company."
        )
    else:
        if "year_normalized" not in trends.columns:
            st.warning(
                "The year_normalized column is missing from "
                "financial_ratios_calculated."
            )
        else:
            trends["year_normalized"] = pd.to_numeric(
                trends["year_normalized"],
                errors="coerce",
            )

            trends = trends.dropna(
                subset=["year_normalized"]
            )

            available_metrics = [
                col
                for col in trends.columns
                if col != "year_normalized"
                and pd.api.types.is_numeric_dtype(trends[col])
                and trends[col].notna().any()
            ]

            if not available_metrics:
                st.info(
                    "No numeric financial metrics are available "
                    "for trend analysis."
                )
            else:
                # Prefer commonly useful growth metrics when present.
                preferred_metrics = [
                    "revenue_growth_pct",
                    "profit_growth_pct",
                    "operating_profit_growth_pct",
                    "revenue_cagr_3y_pct",
                    "profit_cagr_3y_pct",
                    "revenue_cagr_5y_pct",
                    "profit_cagr_5y_pct",
                ]

                default_metrics = [
                    metric
                    for metric in preferred_metrics
                    if metric in available_metrics
                ]

                if not default_metrics:
                    default_metrics = available_metrics[:3]

                selected_metrics = st.multiselect(
                    "Select financial metrics",
                    options=available_metrics,
                    default=default_metrics,
                )

                if selected_metrics:
                    chart_data = trends[
                        ["year_normalized"] + selected_metrics
                    ].copy()

                    chart_data = chart_data.sort_values(
                        "year_normalized"
                    )

                    chart_data["year_normalized"] = (
                        chart_data["year_normalized"]
                        .astype(int)
                        .astype(str)
                    )

                    chart_data = chart_data.set_index(
                        "year_normalized"
                    )

                    st.line_chart(chart_data)

                    with st.expander(
                        "View financial growth data"
                    ):
                        st.dataframe(
                            trends[
                                ["year_normalized"]
                                + selected_metrics
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
                else:
                    st.info(
                        "Select at least one metric to display the chart."
                    )

except Exception as error:
    st.error("Unable to load stock trends.")
    st.exception(error)
