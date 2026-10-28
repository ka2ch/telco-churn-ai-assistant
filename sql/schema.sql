-- Telco Churn database schema
-- One customer = one row in each table, linked by customer_id.

DROP TABLE IF EXISTS billing;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS customers;

-- Who the customer is, and whether they left
CREATE TABLE customers (
    customer_id      TEXT PRIMARY KEY,
    gender           TEXT,
    senior_citizen   INTEGER,   -- 1 = yes, 0 = no
    has_partner      INTEGER,   -- 1 = yes, 0 = no
    has_dependents   INTEGER,   -- 1 = yes, 0 = no
    tenure_months    INTEGER,   -- how many months they have been a customer
    churned          INTEGER    -- 1 = left, 0 = stayed
);

-- What services they use
CREATE TABLE services (
    customer_id        TEXT PRIMARY KEY REFERENCES customers(customer_id),
    phone_service      INTEGER,  -- 1 = yes, 0 = no
    multiple_lines     INTEGER,  -- 1 = yes, 0 = no (or no phone service)
    internet_service   TEXT,     -- 'DSL', 'Fiber optic', or 'No'
    online_security    INTEGER,  -- 1 = yes, 0 = no (or no internet)
    online_backup      INTEGER,
    device_protection  INTEGER,
    tech_support       INTEGER,
    streaming_tv       INTEGER,
    streaming_movies   INTEGER
);

-- Contract and money
CREATE TABLE billing (
    customer_id        TEXT PRIMARY KEY REFERENCES customers(customer_id),
    contract           TEXT,     -- 'Month-to-month', 'One year', 'Two year'
    paperless_billing  INTEGER,  -- 1 = yes, 0 = no
    payment_method     TEXT,
    monthly_charges    REAL,     -- dollars per month
    total_charges      REAL      -- dollars paid so far
);
