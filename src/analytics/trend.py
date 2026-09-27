import pandas as pd

INPUT_FILE = "data/processed/financial_ratios_calculated.csv"
OUTPUT_FILE = "data/processed/trend_growth_analytics.csv"

CAGR_COLUMNS = [
    "revenue_cagr_3y_pct",
    "revenue_cagr_5y_pct",
    "revenue_cagr_10y_pct",
    "pat_cagr_3y_pct",
    "pat_cagr_5y_pct",
    "pat_cagr_10y_pct",
    "eps_cagr_3y_pct",
    "eps_cagr_5y_pct",
    "eps_cagr_10y_pct",
]


def main():
    df = pd.read_csv(INPUT_FILE)

    columns = [
        "company_id",
        "year_normalized",
        *CAGR_COLUMNS,
    ]

    available = [column for column in columns if column in df.columns]

    trend_df = df[available].copy()

    trend_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Rows: {len(trend_df)}")
    print(f"Columns: {len(trend_df.columns)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()