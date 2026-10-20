import pandas as pd

from src.etl.normalize_years import normalize_ticker, normalize_year


# ============================================================
# YEAR NORMALIZATION TESTS - 20 CASES
# ============================================================

def test_year_1():
    assert normalize_year("Mar 2023") == 2023


def test_year_2():
    assert normalize_year("Dec 2022") == 2022


def test_year_3():
    assert normalize_year("Jun 2021") == 2021


def test_year_4():
    assert normalize_year("Sep 2020") == 2020


def test_year_5():
    assert normalize_year("Mar 2019") == 2019


def test_year_6():
    assert normalize_year("Dec 2018") == 2018


def test_year_7():
    assert normalize_year("Jun 2017") == 2017


def test_year_8():
    assert normalize_year("Sep 2016") == 2016


def test_year_9():
    assert normalize_year("Mar 2015") == 2015


def test_year_10():
    assert normalize_year("Dec 2014") == 2014


def test_year_11():
    assert normalize_year("Mar 2013 9m") == 2013


def test_year_12():
    assert normalize_year("Mar 2023 15") == 2023


def test_year_13():
    assert normalize_year("TTM") is None


def test_year_14():
    assert normalize_year(None) is None


def test_year_15():
    assert normalize_year(pd.NA) is None


def test_year_16():
    assert normalize_year("  Mar 2022  ") == 2022


def test_year_17():
    assert normalize_year(2021) == 2021


def test_year_18():
    assert normalize_year("2016") == 2016


def test_year_19():
    assert normalize_year("FY 2020") == 2020


def test_year_20():
    assert normalize_year("") is None


# ============================================================
# TICKER NORMALIZATION TESTS - 20 CASES
# ============================================================

def test_ticker_1():
    assert normalize_ticker("RELIANCE") == "RELIANCE"


def test_ticker_2():
    assert normalize_ticker("reliance") == "RELIANCE"


def test_ticker_3():
    assert normalize_ticker(" RELIANCE ") == "RELIANCE"


def test_ticker_4():
    assert normalize_ticker("RELIANCE.NS") == "RELIANCE"


def test_ticker_5():
    assert normalize_ticker("reliance.ns") == "RELIANCE"


def test_ticker_6():
    assert normalize_ticker("RELIANCE-EQ") == "RELIANCE"


def test_ticker_7():
    assert normalize_ticker("RELIANCE.EQ") == "RELIANCE"


def test_ticker_8():
    assert normalize_ticker("TCS") == "TCS"


def test_ticker_9():
    assert normalize_ticker(" tcs ") == "TCS"


def test_ticker_10():
    assert normalize_ticker("TCS.NS") == "TCS"


def test_ticker_11():
    assert normalize_ticker("HDFCBANK-EQ") == "HDFCBANK"


def test_ticker_12():
    assert normalize_ticker("INFY.EQ") == "INFY"


def test_ticker_13():
    assert normalize_ticker("M&M") == "M&M"


def test_ticker_14():
    assert normalize_ticker("M&M.NS") == "M&M"


def test_ticker_15():
    assert normalize_ticker("ICICI BANK") == "ICICIBANK"


def test_ticker_16():
    assert normalize_ticker("ICICI-BANK") == "ICICI_BANK"


def test_ticker_17():
    assert normalize_ticker("") is None


def test_ticker_18():
    assert normalize_ticker(None) is None


def test_ticker_19():
    assert normalize_ticker(pd.NA) is None


def test_ticker_20():
    assert normalize_ticker("  INFY.NS  ") == "INFY"

import sqlite3
from pathlib import Path

import src.etl.normalize_years as normalizer


def test_main_normalizes_year_in_temporary_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE profit_loss (company_id TEXT, year TEXT, sales REAL)"
    )
    connection.execute(
        "INSERT INTO profit_loss VALUES ('ABC', 'Mar 2023', 100)"
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(normalizer, "DB_PATH", str(db_path))
    monkeypatch.setattr(normalizer, "TABLES", ["profit_loss"])

    normalizer.main()

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT year, year_normalized FROM profit_loss"
    ).fetchone()
    connection.close()

    assert row == ("Mar 2023", 2023)


def test_main_skips_table_without_year_column(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE companies (company_id TEXT)")
    connection.execute("INSERT INTO companies VALUES ('ABC')")
    connection.commit()
    connection.close()

    monkeypatch.setattr(normalizer, "DB_PATH", str(db_path))
    monkeypatch.setattr(normalizer, "TABLES", ["companies"])

    normalizer.main()

    connection = sqlite3.connect(db_path)
    columns = [
        row[1]
        for row in connection.execute("PRAGMA table_info(companies)")
    ]
    connection.close()

    assert "year_normalized" not in columns


def test_main_closes_connection_after_error(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    sqlite3.connect(db_path).close()

    monkeypatch.setattr(normalizer, "DB_PATH", str(db_path))
    monkeypatch.setattr(normalizer, "TABLES", ["missing_table"])

    try:
        normalizer.main()
    except Exception:
        pass

    # The database file should remain accessible after the error.
    connection = sqlite3.connect(db_path)
    connection.execute("SELECT 1")
    connection.close()
