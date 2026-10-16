
from fastapi import FastAPI

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="API for Nifty 100 financial analysis",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Nifty 100 Financial Intelligence API is running",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "nifty100.db"


@app.get("/companies")
def get_companies():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute("""
            SELECT id, company_name, website,
                   face_value, book_value,
                   roce_percentage, roe_percentage
            FROM companies
            ORDER BY company_name
        """).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()

from fastapi import HTTPException


@app.get("/companies/{company_id}")
def get_company(company_id: str):
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        row = connection.execute(
            """
            SELECT *
            FROM companies
            WHERE id = ?
            """,
            (company_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )

        return dict(row)
    finally:
        connection.close()
