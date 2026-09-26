from pathlib import Path
import pandas as pd


RAW_DIR = Path("data/raw")


def inspect_excel_files():
    """Inspect all Excel files in the raw data folder."""
    files = list(RAW_DIR.glob("*.xlsx"))

    if not files:
        print("No Excel files found in data/raw")
        return

    for file in sorted(files):
        print("\n" + "=" * 70)
        print(f"FILE: {file.name}")
        print("=" * 70)

        excel = pd.ExcelFile(file)

        for sheet in excel.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet, header=1)

            print(f"SHEET: {sheet}")
            print(f"ROWS: {len(df)}")
            print(f"COLUMNS: {len(df.columns)}")
            print("COLUMN NAMES:")
            print(list(df.columns))


if __name__ == "__main__":
    inspect_excel_files()