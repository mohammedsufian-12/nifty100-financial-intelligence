import os

import pandas as pd


FILE_PATH = "data/processed/trend_growth_analytics.csv"


def test_trend_file_exists():
    assert os.path.exists(FILE_PATH)


def test_trend_file_not_empty():
    df = pd.read_csv(FILE_PATH)
    assert not df.empty


def test_required_cagr_columns_exist():
    df = pd.read_csv(FILE_PATH)

    required = {
        "revenue_cagr_3y_pct",
        "revenue_cagr_5y_pct",
        "revenue_cagr_10y_pct",
        "pat_cagr_3y_pct",
        "pat_cagr_5y_pct",
        "pat_cagr_10y_pct",
        "eps_cagr_3y_pct",
        "eps_cagr_5y_pct",
        "eps_cagr_10y_pct",
    }

    assert required.issubset(df.columns)


def test_company_year_records_exist():
    df = pd.read_csv(FILE_PATH)

    assert "company_id" in df.columns
    assert "year_normalized" in df.columns