# Telco Churn AI Assistant

Predict which telecom customers are likely to cancel their service, and ask questions about them in plain English — an AI assistant turns your question into SQL, runs it, and explains the answer.

> *"Show me the 20 highest-risk customers on month-to-month contracts."*
> → AI writes the SQL → runs it on the database → returns the list with a short explanation

## Why I built this

I worked for about six years as a sales associate at a Bell Canada authorized dealer. In the store, I often saw signs that a customer was about to leave — contracts ending, complaints about the bill, competitor promotions. This project checks those on-the-floor instincts against real data, and builds a tool that store or retention staff could actually use.

## What it does

| Part | Description | Status |
|---|---|---|
| 1. Data pipeline | Load the raw CSV, clean it, and split it into SQL tables | ✅ Done |
| 2. SQL analysis | Explore churn patterns with SQL queries | ✅ Done |
| 3. Churn model | Predict churn risk and explain *why* each customer is at risk | ⬜ To do |
| 4. AI assistant | Ask questions in plain English → SQL → answer | ⬜ To do |
| 5. Dashboard | Streamlit app with key numbers, charts, risk list, and chat | ⬜ To do |

## Tech stack

Python · SQLite · pandas · scikit-learn · XGBoost · SHAP · LLM API · Streamlit

## Data

[IBM Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) — about 7,000 customers with contract type, services, monthly charges, tenure, and whether they left.

The data is not stored in this repo. To get it:

1. Download the CSV from the Kaggle link above
2. Put it in the `data/` folder as `data/WA_Fn-UseC_-Telco-Customer-Churn.csv`

**Known limitation:** the dataset has no dates, so questions like "this month" are handled by ranking customers by risk score instead of by time.

## Project structure

```
telco-churn-ai-assistant/
├── data/         # raw data (not committed)
├── notebooks/    # exploration and experiments
├── sql/          # table definitions and analysis queries
├── src/          # pipeline, model, and AI assistant code
├── app/          # Streamlit dashboard
└── requirements.txt
```

## How to run

```bash
git clone https://github.com/ka2ch/telco-churn-ai-assistant.git
cd telco-churn-ai-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add your API key to .env
```

Then build the database and run the analysis:

```bash
python src/load_data.py       # CSV -> data/telco.db (3 tables)
python src/run_analysis.py    # runs every query in sql/analysis.sql
```

More steps will be added as each part is built.

## Results

### SQL analysis — key findings

All numbers come from [`sql/analysis.sql`](sql/analysis.sql) on 7,043 customers. Overall churn rate: **26.5%**.

| Finding | Churn rate |
|---|---|
| **Contract type matters most.** Month-to-month vs two-year contracts | 42.7% vs 2.8% |
| **The first year is the danger zone.** 0–12 months vs 49+ months as a customer | 47.4% vs 9.5% |
| **Fiber customers leave more** than DSL customers, despite the premium service | 41.9% vs 19.0% |
| **Payment method is a strong signal.** Electronic check vs automatic credit card | 45.3% vs 15.2% |
| **Add-on services keep customers.** Internet customers with neither tech support nor online security vs both | 49.0% vs 9.0% |
| **High-risk segment:** month-to-month + fiber + no tech support (25% of customers) vs everyone else | 57.5% vs 15.9% |

- Customers who left paid **$13 more per month** on average ($74.44 vs $61.27) and had been customers for **half as long** (18 vs 38 months).
- Churned customers are 26.5% of the base but **30.5% of monthly revenue (~$139K of $456K)**, because higher-paying customers leave more often.

**Note:** these are patterns, not proven causes. For example, customers on automatic payment are also more likely to be on long contracts. The churn model in Part 3 looks at all factors together to separate the strongest signals.

**Compared with my store experience:** month-to-month customers and customers with high bills were the ones most often asking about cancelling or switching. The data strongly supports both.
