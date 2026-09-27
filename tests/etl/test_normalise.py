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