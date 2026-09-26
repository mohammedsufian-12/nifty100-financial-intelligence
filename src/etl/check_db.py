import sqlite3

connection = sqlite3.connect("nifty100.db")

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("TABLES IN DATABASE:")
for table in tables:
    print(table[0])

connection.close()