
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Annual Reports | Nifty 100",
    page_icon="📄",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


# --------------------------------------------------
# DATABASE FUNCTION
# --------------------------------------------------

@st.cache_data
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        query = """
            SELECT
                c.id AS company_id,
                c.company_name,
                d.year,
                d.annual_report
            FROM companies AS c
            LEFT JOIN documents AS d
                ON d.company_id = c.id
            ORDER BY c.company_name, d.year DESC
        """
        return pd.read_sql_query(query, conn)


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("📄 Annual Reports")
st.caption(
    "Find company annual reports and open available report links."
)


# --------------------------------------------------
# LOAD REPORTS
# --------------------------------------------------

try:
    reports = load_data()

    if reports.empty:
        st.warning("No company or annual report records were found.")
        st.stop()

    reports["year"] = reports["year"].fillna("").astype(str)

    reports["annual_report"] = (
        reports["annual_report"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        company_options = (
            reports[["company_id", "company_name"]]
            .drop_duplicates()
            .sort_values("company_name")
        )

        company_labels = company_options["company_name"].tolist()

        selected_company = st.selectbox(
            "Select company",
            company_labels,
        )

    selected_company_id = company_options.loc[
        company_options["company_name"] == selected_company,
        "company_id",
    ].iloc[0]

    company_reports = reports[
        reports["company_id"] == selected_company_id
    ].copy()

    with col2:
        years = sorted(
            [
                year
                for year in company_reports["year"].unique()
                if year.strip()
            ],
            reverse=True,
        )

        year_options = ["All years"] + years

        selected_year = st.selectbox(
            "Select financial year",
            year_options,
        )

    if selected_year != "All years":
        filtered_reports = company_reports[
            company_reports["year"] == selected_year
        ].copy()
    else:
        filtered_reports = company_reports.copy()

    st.divider()

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    available_reports = filtered_reports[
        filtered_reports["annual_report"] != ""
    ]

    missing_reports = filtered_reports[
        filtered_reports["annual_report"] == ""
    ]

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric(
        "Report records",
        len(filtered_reports),
    )

    metric2.metric(
        "Available report links",
        len(available_reports),
    )

    metric3.metric(
        "Missing report links",
        len(missing_reports),
    )

    st.divider()

    # --------------------------------------------------
    # REPORT LINKS
    # --------------------------------------------------

    st.subheader(f"Reports for {selected_company}")

    if filtered_reports.empty:
        st.info("No report records were found for this selection.")

    else:
        for _, row in filtered_reports.iterrows():
            report_year = row["year"] or "Year not specified"
            report_url = row["annual_report"]

            with st.container(border=True):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Financial year: {report_year}**")

                    if report_url:
                        st.markdown(
                            f"[Open annual report PDF]({report_url})"
                        )
                    else:
                        st.warning("Annual report link is missing.")

                with col2:
                    if report_url:
                        st.link_button(
                            "Open report",
                            report_url,
                            use_container_width=True,
                        )
                    else:
                        st.caption("Not available")

    st.divider()

    # --------------------------------------------------
    # FULL REPORT TABLE
    # --------------------------------------------------

    st.subheader("Annual Report Register")

    display_data = filtered_reports[
        ["company_name", "year", "annual_report"]
    ].copy()

    display_data["status"] = display_data[
        "annual_report"
    ].apply(
        lambda url: "Available" if url else "Missing"
    )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "annual_report": st.column_config.LinkColumn(
                "Annual Report URL",
                display_text="Open report",
            ),
            "status": st.column_config.TextColumn(
                "Report Status"
            ),
        },
    )

    # --------------------------------------------------
    # DOWNLOAD CSV
    # --------------------------------------------------

    csv_data = display_data.to_csv(index=False)

    st.download_button(
        label="Download Annual Report Register",
        data=csv_data,
        file_name="annual_report_register.csv",
        mime="text/csv",
    )

except Exception as error:
    st.error("Unable to load annual reports.")
    st.exception(error)
