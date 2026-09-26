import pandas as pd


FILE_PATH = "data/processed/screener_output.csv"


def test_screener_file_exists():
    df = pd.read_csv(FILE_PATH)
    assert not df.empty


def test_all_six_presets_exist():
    df = pd.read_csv(FILE_PATH)

    expected = {
        "quality_compounder",
        "value_pick",
        "growth_accelerator",
        "dividend_champion",
        "debt_free_blue_chip",
        "turnaround_watch",
    }

    assert expected.issubset(set(df["preset"].unique()))


def test_composite_score_exists():
    df = pd.read_csv(FILE_PATH)

    assert "composite_score" in df.columns


def test_composite_score_range():
    df = pd.read_csv(FILE_PATH)

    scores = pd.to_numeric(
        df["composite_score"],
        errors="coerce",
    ).dropna()

    assert scores.between(0, 100).all()


def test_no_duplicate_company_preset():
    df = pd.read_csv(FILE_PATH)

    duplicates = df.duplicated(
        subset=["company_id", "preset"]
    ).sum()

    assert duplicates == 0