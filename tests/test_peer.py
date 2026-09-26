import pandas as pd

PERCENTILE_FILE = "data/processed/peer_percentiles.csv"
EXCEL_FILE = "data/processed/peer_comparison.xlsx"


def test_peer_percentile_file_exists():
    df = pd.read_csv(PERCENTILE_FILE)
    assert not df.empty


def test_peer_percentile_has_required_columns():
    df = pd.read_csv(PERCENTILE_FILE)

    required = {
        "company_id",
        "peer_group",
        "metric",
        "value",
        "percentile_rank",
    }

    assert required.issubset(df.columns)


def test_all_11_peer_groups_exist():
    df = pd.read_csv(PERCENTILE_FILE)
    assert df["peer_group"].nunique() == 11


def test_percentile_range():
    df = pd.read_csv(PERCENTILE_FILE)

    values = pd.to_numeric(
        df["percentile_rank"],
        errors="coerce",
    ).dropna()

    assert values.between(0, 100).all()


def test_peer_comparison_excel_exists():
    import os

    assert os.path.exists(EXCEL_FILE)