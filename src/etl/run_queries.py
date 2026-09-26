import sqlite3
from pathlib import Path

DB_PATH = "nifty100.db"
SQL_FILE = Path("src/sql/exploratory_queries.sql")

connection = sqlite3.connect(DB_PATH)

sql = SQL_FILE.read_text(encoding="utf-8")

queries = [
    query.strip()
    for query in sql.split(";")
    if query.strip()
]

print(f"Running {len(queries)} queries...\n")

for number, query in enumerate(queries, start=1):
    print(f"--- Query {number} ---")

    try:
        cursor = connection.execute(query)
        rows = cursor.fetchall()

        for row in rows[:10]:
            print(row)

        print(f"Rows returned: {len(rows)}\n")

    except Exception as error:
        print(f"ERROR: {error}\n")

connection.close()

print("ALL QUERIES COMPLETED")