"""
Step 3: Train a churn prediction model, give every customer a risk score
with the top reasons, and save the results back into the database.

Run from the project folder:
    python src/train_model.py

What it does:
  1. Pulls customer data out of SQLite (joining the 3 tables)
  2. Trains two models and compares them on customers the model has never seen:
       - Logistic Regression (simple, easy to explain)
       - XGBoost (more powerful, catches combinations of factors)
  3. Picks the better one
  4. Gives every customer an honest risk score (each score comes from a model
     that did NOT see that customer during training)
  5. Finds the top 3 reasons behind each customer's risk
  6. Saves everything to a new table: churn_predictions
"""

import json
import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "telco.db"
MODEL_DIR = ROOT / "models"
RANDOM_SEED = 42

# Risk level cut-offs (probability of leaving)
HIGH_RISK = 0.50
MEDIUM_RISK = 0.25


# ---------------------------------------------------------------------------
# 1. Get the data
# ---------------------------------------------------------------------------
DATA_SQL = """
SELECT c.customer_id,
       c.senior_citizen, c.has_partner, c.has_dependents, c.tenure_months,
       s.phone_service, s.multiple_lines, s.internet_service,
       s.online_security, s.online_backup, s.device_protection,
       s.tech_support, s.streaming_tv, s.streaming_movies,
       b.contract, b.paperless_billing, b.payment_method,
       b.monthly_charges, b.total_charges,
       c.churned
FROM customers c
JOIN services s ON c.customer_id = s.customer_id
JOIN billing  b ON c.customer_id = b.customer_id
"""
# Note: gender is left out on purpose. It barely predicts churn, and deciding
# who gets retention offers based on gender isn't something a company should do.

TEXT_COLUMNS = ["internet_service", "contract", "payment_method"]


def load_data():
    if not DB_PATH.exists():
        raise FileNotFoundError("Database not found. Run `python src/load_data.py` first.")
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(DATA_SQL, conn)

    ids = df["customer_id"]
    y = df["churned"].astype(int)
    # Models need numbers, so text columns become Yes/No (1/0) columns,
    # e.g. contract -> contract_Month-to-month, contract_One year, contract_Two year
    X = pd.get_dummies(df.drop(columns=["customer_id", "churned"]), columns=TEXT_COLUMNS).astype(float)
    return df, ids, X, y


# ---------------------------------------------------------------------------
# 2. Models
# ---------------------------------------------------------------------------
def make_models():
    return {
        "Logistic Regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, random_state=RANDOM_SEED)
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=RANDOM_SEED,
        ),
    }


def evaluate(y_true, prob):
    pred = (prob >= HIGH_RISK).astype(int)
    return {
        "auc": round(roc_auc_score(y_true, prob), 3),
        "recall": round(recall_score(y_true, pred), 3),
        "precision": round(precision_score(y_true, pred, zero_division=0), 3),
        "accuracy": round(accuracy_score(y_true, pred), 3),
    }


def compare_models(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_SEED
    )
    results = {}
    for name, model in make_models().items():
        model.fit(X_train, y_train)
        results[name] = evaluate(y_test, model.predict_proba(X_test)[:, 1])

    print("\nModel comparison (on 20% of customers the models never saw):")
    print(pd.DataFrame(results).T.to_string())
    print(
        "\n  auc       = how well it ranks risky customers above safe ones (0.5 = guessing, 1.0 = perfect)"
        "\n  recall    = of customers who actually left, how many it flagged"
        "\n  precision = of customers it flagged, how many actually left"
    )

    best = max(results, key=lambda n: results[n]["auc"])
    print(f"\nBest model: {best}")
    return best, results


# ---------------------------------------------------------------------------
# 3. Reasons: how much each factor pushed a customer's risk up or down
# ---------------------------------------------------------------------------
def factor_contributions(model, name, X):
    if name == "XGBoost":
        contribs = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
        return contribs[:, :-1]  # last column is the baseline, not a factor
    scaler, logreg = model[0], model[-1]
    return scaler.transform(X) * logreg.coef_[0]


FLAG_LABELS = {
    "senior_citizen": "Senior citizen",
    "has_partner": "Partner",
    "has_dependents": "Dependents",
    "phone_service": "Phone service",
    "multiple_lines": "Multiple lines",
    "online_security": "Online security",
    "online_backup": "Online backup",
    "device_protection": "Device protection",
    "tech_support": "Tech support",
    "streaming_tv": "Streaming TV",
    "streaming_movies": "Streaming movies",
    "paperless_billing": "Paperless billing",
}


def describe(feature: str, value: float) -> str:
    """Turn a model column + the customer's value into a plain-English reason."""
    if feature == "tenure_months":
        months = int(value)
        unit = "month" if months == 1 else "months"
        return f"Customer for only {months} {unit}" if months < 24 else f"Customer for {months} {unit}"
    if feature == "monthly_charges":
        return f"Monthly bill ${value:.0f}"
    if feature == "total_charges":
        return f"Total paid so far ${value:.0f}"
    if feature in FLAG_LABELS:
        label = FLAG_LABELS[feature]
        return label if value == 1 else f"No {label.lower()}"

    if feature.startswith("contract_"):
        cat = feature[len("contract_"):]
        return f"{cat} contract" if value == 1 else f"Not on a {cat.lower()} contract"
    if feature.startswith("internet_service_"):
        cat = feature[len("internet_service_"):]
        if cat == "No":
            return "No internet service" if value == 1 else "Has internet service"
        return f"{cat} internet" if value == 1 else f"Not on {cat} internet"
    if feature.startswith("payment_method_"):
        cat = feature[len("payment_method_"):]
        return f"Pays by {cat.lower()}" if value == 1 else f"Doesn't pay by {cat.lower()}"
    return f"{feature} = {value}"


def top_reasons(contribs, X, n=3):
    reasons = []
    columns = X.columns
    values = X.to_numpy()
    for i in range(len(X)):
        order = np.argsort(-contribs[i])
        row = [describe(columns[j], values[i, j]) for j in order[:n] if contribs[i, j] > 0]
        reasons.append(row + [None] * (n - len(row)))
    return reasons


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main():
    df, ids, X, y = load_data()
    print(f"Loaded {len(X):,} customers, {X.shape[1]} model inputs")

    best_name, results = compare_models(X, y)
    best_model = make_models()[best_name]

    # Honest scores: split customers into 5 groups; each group is scored by a
    # model trained on the other 4, so no customer is scored by a model that saw them.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    prob = cross_val_predict(clone(best_model), X, y, cv=cv, method="predict_proba")[:, 1].astype(float)
    print(f"\nScores for all customers (5-fold): {evaluate(y, prob)}")

    # Final model on everyone, used for reasons (and later, scoring new customers)
    best_model.fit(X, y)
    contribs = factor_contributions(best_model, best_name, X)
    reasons = top_reasons(contribs, X)

    # Which factors matter most overall
    importance = (
        pd.Series(np.abs(contribs).mean(axis=0), index=X.columns)
        .sort_values(ascending=False)
        .head(10)
        .round(3)
    )
    print("\nTop 10 factors overall (bigger = more influence on risk):")
    print(importance.to_string())

    # Save predictions to the database
    predictions = pd.DataFrame({
        "customer_id": ids,
        "churn_risk_pct": (prob * 100).round(1),
        "risk_level": np.where(prob >= HIGH_RISK, "High", np.where(prob >= MEDIUM_RISK, "Medium", "Low")),
        "reason_1": [r[0] for r in reasons],
        "reason_2": [r[1] for r in reasons],
        "reason_3": [r[2] for r in reasons],
    })
    with sqlite3.connect(DB_PATH) as conn:
        predictions.to_sql("churn_predictions", conn, if_exists="replace", index=False)
    print(f"\nSaved {len(predictions):,} risk scores to the churn_predictions table")

    # Save the model and the results
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": best_model, "name": best_name, "columns": list(X.columns)},
                MODEL_DIR / "churn_model.joblib")
    (MODEL_DIR / "metrics.json").write_text(json.dumps({
        "best_model": best_name,
        "test_results": results,
        "top_factors": importance.to_dict(),
    }, indent=2))
    print(f"Saved model and metrics to {MODEL_DIR}")

    # The list a retention team would actually use: customers who are still here
    current = predictions[df["churned"].values == 0]
    print("\nCurrent customers (not yet left) by risk level:")
    print(current["risk_level"].value_counts().reindex(["High", "Medium", "Low"]).to_string())
    print("\nTop 5 current customers most likely to leave:")
    print(current.sort_values("churn_risk_pct", ascending=False).head(5).to_string(index=False))


if __name__ == "__main__":
    main()
