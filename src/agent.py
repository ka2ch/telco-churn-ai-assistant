"""
Step 4: AI assistant that answers questions about customers by writing SQL.

How it works:
  1. You ask a question in plain English (or Korean)
  2. Claude reads a description of the database and writes a SQL query
  3. The query runs on the database in READ-ONLY mode (it can't change anything)
  4. Claude reads the results and answers in plain language
  (If the first query isn't enough, Claude can run a few more.)

Setup: put your API key in a .env file in the project folder:
    ANTHROPIC_API_KEY=your-key

Run from the project folder:
    python src/agent.py
"""

import json
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "telco.db"
load_dotenv(ROOT / ".env")

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_ROWS_TO_CLAUDE = 50   # Claude only sees the first 50 rows of a result
MAX_STEPS = 6             # max number of queries per question


# ---------------------------------------------------------------------------
# Database access (read-only)
# ---------------------------------------------------------------------------
def connect_readonly() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError("Database not found. Run load_data.py and train_model.py first.")
    # mode=ro: the database itself refuses any change, even if a bad query slips through
    return sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)


BLOCKED_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum)\b", re.IGNORECASE
)


def run_sql(query: str):
    """Run one SELECT query safely. Returns (result for Claude, full DataFrame or None)."""
    q = query.strip().rstrip(";").strip()
    if ";" in q:
        return {"error": "Only one query at a time."}, None
    if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
        return {"error": "Only SELECT queries are allowed."}, None
    if BLOCKED_WORDS.search(q):
        return {"error": "This query contains a blocked keyword. Only read data."}, None

    conn = connect_readonly()
    try:
        df = pd.read_sql_query(q, conn)
    except Exception as e:  # send the error back so Claude can fix its query
        return {"error": str(e)}, None
    finally:
        conn.close()

    result = {
        "row_count": len(df),
        "rows": df.head(MAX_ROWS_TO_CLAUDE).to_dict(orient="records"),
        "truncated": len(df) > MAX_ROWS_TO_CLAUDE,
    }
    return result, df


def schema_text() -> str:
    """Read the real table and column names from the database."""
    conn = connect_readonly()
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        lines = []
        for t in tables:
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
            lines.append(f"{t}(" + ", ".join(f"{c[1]} {c[2]}" for c in cols) + ")")
        return "\n".join(lines)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Instructions for Claude
# ---------------------------------------------------------------------------
COLUMN_NOTES = """
All tables join on customer_id. One row per customer in every table.

customers: churned 1 = customer has left, 0 = still a customer.
           senior_citizen, has_partner, has_dependents: 1 = yes, 0 = no.
           tenure_months = how many months they have been a customer.
services:  1/0 columns for each service. internet_service is 'DSL', 'Fiber optic', or 'No'.
billing:   contract is 'Month-to-month', 'One year', or 'Two year'.
           payment_method is 'Electronic check', 'Mailed check',
           'Bank transfer (automatic)', or 'Credit card (automatic)'.
           monthly_charges and total_charges are in dollars.
churn_predictions: churn_risk_pct = model's estimated chance (0-100) the customer leaves.
           risk_level is 'High' (>= 50), 'Medium' (25-50), or 'Low' (< 25).
           reason_1..reason_3 = top reasons for that customer's risk, in plain English.
"""

SYSTEM_PROMPT = f"""You are a data assistant for a telecom company's customer retention team.
Staff ask questions about customers; you answer by querying a SQLite database with the run_sql tool.

Database tables:
{{schema}}

Column notes:
{COLUMN_NOTES}

Rules:
- Always get numbers from the database with run_sql. Never guess or invent numbers.
- When asked about at-risk or high-risk customers, use churn_predictions and only include
  customers who are still here (customers.churned = 0), unless the user asks about past customers.
- The data has NO dates. If asked about "this month", "last week", etc., briefly say there are no
  dates in the data and answer with the closest useful thing (for example, current high-risk customers).
- For lists of customers, include customer_id, churn risk, and the reasons when relevant,
  and use LIMIT (default 10) unless the user asks for more.
- If a query fails, read the error, fix the query, and try again.
- Answer in the same language the user used. Keep answers short and clear for non-technical staff.
  Lead with the direct answer, then key numbers. Use a small table for lists.
"""

TOOLS = [{
    "name": "run_sql",
    "description": "Run one read-only SQLite SELECT query on the customer database and return the rows.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A single SQLite SELECT query."}
        },
        "required": ["query"],
    },
}]


# ---------------------------------------------------------------------------
# The question -> SQL -> answer loop
# ---------------------------------------------------------------------------
def ask(question: str, history: list | None = None, client: Anthropic | None = None) -> dict:
    """
    Answer one question.
    Returns: answer (text), queries (SQL that ran), table (last result as DataFrame),
             messages (pass back in as `history` to keep the conversation going).
    """
    client = client or Anthropic()
    system = SYSTEM_PROMPT.replace("{schema}", schema_text())
    messages = list(history or []) + [{"role": "user", "content": question}]
    queries, last_table = [], None

    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text").strip()
            return {"answer": answer, "queries": queries, "table": last_table, "messages": messages}

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            query = block.input.get("query", "")
            result, table = run_sql(query)
            queries.append(query)
            if table is not None:
                last_table = table
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
                "is_error": "error" in result,
            })
        messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "Sorry, I couldn't finish answering that. Try asking in a simpler way.",
        "queries": queries, "table": last_table, "messages": messages,
    }


# ---------------------------------------------------------------------------
# Chat in the terminal
# ---------------------------------------------------------------------------
def main():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key == "your-key-here":
        print("No API key found. Create a .env file with: ANTHROPIC_API_KEY=your-key")
        return

    print(f"Churn assistant ready (model: {MODEL}). Type a question, or 'quit' to exit.\n")
    history = []
    while True:
        question = input("You: ").strip()
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        try:
            result = ask(question, history)
        except Exception as e:
            print(f"\n[Error] {e}\n")
            continue
        history = result["messages"]
        for q in result["queries"]:
            print(f"\n[SQL]\n{q}")
        print(f"\nAssistant: {result['answer']}\n")


if __name__ == "__main__":
    main()
