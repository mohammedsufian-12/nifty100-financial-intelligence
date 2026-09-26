import pandas as pd


FILE_PATH = "data/processed/financial_ratios_calculated.csv"


def test_ratio_file_exists():
    df = pd.read_csv(FILE_PATH)

    assert not df.empty


def test_ratio_has_expected_rows():
    df = pd.read_csv(FILE_PATH)

    assert len(df) > 0


def test_ratio_has_50_plus_kpis():
    df = pd.read_csv(FILE_PATH)

    # company_id + year_normalized are identifiers,
    # so the remaining columns are KPI/output columns.
    kpi_count = len(df.columns) - 2

    assert kpi_count >= 50


def test_no_duplicate_company_year():
    df = pd.read_csv(FILE_PATH)

    duplicates = df.duplicated(
        subset=["company_id", "year_normalized"]
    ).sum()

    assert duplicates == 0


def test_required_kpis_exist():
    df = pd.read_csv(FILE_PATH)

    required_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_assets_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "revenue_cagr_3y_pct",
        "revenue_cagr_5y_pct",
        "revenue_cagr_10y_pct",
        "pat_cagr_3y_pct",
        "pat_cagr_5y_pct",
        "pat_cagr_10y_pct",
        "capital_allocation_pattern",
    ]

    for column in required_columns:
        assert column in df.columns