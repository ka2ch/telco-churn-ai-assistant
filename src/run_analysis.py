"""
Step 2: Run every query in sql/analysis.sql and print the results.

Run from the project folder:
    python src/run_analysis.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "telco.db"
ANALYSIS_PATH = ROOT / "sql" / "analysis.sql"


def read_queries(path: Path) -> list[tuple[str, str]]:
    """Split the .sql file into (name, query) pairs using '-- name:' markers."""
    queries = []
    name, lines = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("-- name:"):
            if name:
                queries.append((name, "\n".join(lines).strip()))
            name, lines = line.split("-- name:", 1)[1].strip(), []
        elif name:
            lines.append(line)
    if name:
        queries.append((name, "\n".join(lines).strip()))
    return queries


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("Database not found. Run `python src/load_data.py` first.")

    with sqlite3.connect(DB_PATH) as conn:
        for name, query in read_queries(ANALYSIS_PATH):
            print("=" * 60)
            print(name)
            print("-" * 60)
            print(pd.read_sql_query(query, conn).to_string(index=False))
            print()


if __name__ == "__main__":
    main()
