# Telco Churn AI Assistant

Predict which telecom customers are likely to cancel their service, and ask questions about them in plain English — an AI assistant turns your question into SQL, runs it, and explains the answer.

> *"Show me the 20 highest-risk customers on month-to-month contracts."*
> → AI writes the SQL → runs it on the database → returns the list with a short explanation

## Why I built this

I worked for about six years as a sales associate at a Bell Canada authorized dealer. In the store, I often saw signs that a customer was about to leave — contracts ending, complaints about the bill, competitor promotions. This project checks those on-the-floor instincts against real data, and builds a tool that store or retention staff could actually use.

## What it does

| Part | Description | Status |
|---|---|---|
| 1. Data pipeline | Load the raw CSV, clean it, and split it into SQL tables | ⬜ To do |
| 2. SQL analysis | Explore churn patterns with SQL queries | ⬜ To do |
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

More steps will be added as each part is built.

## Results

*Coming soon.*
