-- ============================================================
-- CreditRisk360 — PostgreSQL schema (Supabase-compatible)
-- Reference date: 2026-08-31 | Scope: CEMAC
-- ============================================================

-- Referential: countries (ISO Alpha-3, CEMAC)
CREATE TABLE IF NOT EXISTS countries (
    country_code VARCHAR(3) PRIMARY KEY,
    name_short_fr VARCHAR(50) NOT NULL,
    name_full_fr VARCHAR(100) NOT NULL,
    sort_order INT DEFAULT 0
);

INSERT INTO countries (country_code, name_short_fr, name_full_fr, sort_order) VALUES
('CMR', 'Cameroun', 'République du Cameroun', 1),
('CAF', 'Centrafrique', 'République centrafricaine', 2),
('COG', 'Congo', 'République du Congo', 3),
('GAB', 'Gabon', 'République gabonaise', 4),
('GNQ', 'Guinée équatoriale', 'République de Guinée équatoriale', 5),
('TCD', 'Tchad', 'République du Tchad', 6)
ON CONFLICT (country_code) DO NOTHING;

-- Reporting institutions
CREATE TABLE IF NOT EXISTS institutions (
    institution_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('BANK', 'MFI')),
    country_hq VARCHAR(3) REFERENCES countries(country_code)
);

-- Borrowers (registration_date/country nullable: missing data is a monitored DQ rule)
CREATE TABLE IF NOT EXISTS borrowers (
    borrower_id VARCHAR(20) PRIMARY KEY,
    borrower_type VARCHAR(20) CHECK (borrower_type IN ('INDIVIDUAL', 'SME', 'CORPORATE')),
    display_name VARCHAR(150) NOT NULL,
    country VARCHAR(3) REFERENCES countries(country_code),
    sector VARCHAR(50) NOT NULL,
    registration_date DATE,
    is_demo BOOLEAN DEFAULT FALSE
);

-- Loans / facilities (outstanding_amount = source of truth for exposure;
-- dates nullable: missing data is a monitored DQ rule)
CREATE TABLE IF NOT EXISTS loans (
    loan_id VARCHAR(20) PRIMARY KEY,
    borrower_id VARCHAR(20) REFERENCES borrowers(borrower_id),
    institution_id VARCHAR(10) REFERENCES institutions(institution_id),
    loan_type VARCHAR(50) NOT NULL,
    principal_amount NUMERIC(15, 2) NOT NULL,
    outstanding_amount NUMERIC(15, 2) NOT NULL,
    interest_rate NUMERIC(5, 2) NOT NULL,
    start_date DATE,
    maturity_date DATE,
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'CLOSED', 'DEFAULTED', 'WRITTEN_OFF')),
    collateral_flag BOOLEAN DEFAULT FALSE,
    restructured_flag BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_loans_borrower ON loans(borrower_id);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);

-- Payments (payment_date nullable: unpaid instalments)
CREATE TABLE IF NOT EXISTS payments (
    payment_id BIGSERIAL PRIMARY KEY,
    loan_id VARCHAR(20) REFERENCES loans(loan_id),
    due_date DATE NOT NULL,
    payment_date DATE,
    amount_due NUMERIC(15, 2) NOT NULL,
    amount_paid NUMERIC(15, 2) NOT NULL,
    days_past_due INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_payments_loan ON payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_payments_due ON payments(due_date);

-- Monthly fact table for vintage / cohort analysis
CREATE TABLE IF NOT EXISTS loan_monthly (
    loan_id VARCHAR(20) REFERENCES loans(loan_id),
    as_of_date DATE NOT NULL,
    outstanding_amount NUMERIC(15, 2) NOT NULL,
    dpd INT DEFAULT 0,
    dpd_bucket VARCHAR(20) NOT NULL,
    PRIMARY KEY (loan_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_loan_monthly_date ON loan_monthly(as_of_date);

-- Credit enquiries (bureau consultations)
CREATE TABLE IF NOT EXISTS enquiries (
    enquiry_id BIGSERIAL PRIMARY KEY,
    borrower_id VARCHAR(20) REFERENCES borrowers(borrower_id),
    institution_id VARCHAR(10) REFERENCES institutions(institution_id),
    enquiry_date DATE NOT NULL,
    purpose VARCHAR(100)
);

-- Application state: data-quality resolution workflow
CREATE TABLE IF NOT EXISTS app_state_dq_resolutions (
    issue_id VARCHAR(50) PRIMARY KEY,
    rule_id VARCHAR(10) NOT NULL,
    record_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'DETECTED'
        CHECK (status IN ('DETECTED', 'INVESTIGATING', 'RESOLVED')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Business views (secured for AI analyst & dashboards)
-- ============================================================

CREATE OR REPLACE VIEW v_loans_enriched AS
SELECT
    l.loan_id,
    l.borrower_id,
    b.display_name AS borrower_name,
    b.borrower_type,
    b.country,
    c.name_short_fr AS country_name,
    b.sector,
    b.registration_date,
    l.institution_id,
    i.name AS institution_name,
    i.type AS institution_type,
    l.loan_type,
    l.principal_amount,
    l.outstanding_amount,
    l.interest_rate,
    l.start_date,
    l.maturity_date,
    l.status,
    l.collateral_flag,
    l.restructured_flag
FROM loans l
JOIN borrowers b ON b.borrower_id = l.borrower_id
JOIN institutions i ON i.institution_id = l.institution_id
JOIN countries c ON c.country_code = b.country;

CREATE OR REPLACE VIEW v_kpi_monthly AS
SELECT
    DATE_TRUNC('month', m.as_of_date)::date AS as_of_month,
    SUM(m.outstanding_amount) AS total_outstanding,
    SUM(CASE WHEN m.dpd >= 90 THEN m.outstanding_amount ELSE 0 END) AS npl_outstanding,
    CASE WHEN SUM(m.outstanding_amount) > 0
         THEN SUM(CASE WHEN m.dpd >= 90 THEN m.outstanding_amount ELSE 0 END)
              / SUM(m.outstanding_amount) * 100
         ELSE 0 END AS npl_ratio,
    SUM(CASE WHEN m.dpd >= 90 THEN 1 ELSE 0 END) AS npl_count,
    COUNT(*) AS loan_count
FROM loan_monthly m
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW v_segment_monthly AS
SELECT
    DATE_TRUNC('month', m.as_of_date)::date AS as_of_month,
    b.country,
    b.sector,
    b.borrower_type,
    SUM(m.outstanding_amount) AS total_outstanding,
    SUM(CASE WHEN m.dpd >= 90 THEN m.outstanding_amount ELSE 0 END) AS npl_outstanding,
    COUNT(*) AS loan_count,
    SUM(CASE WHEN m.dpd >= 90 THEN 1 ELSE 0 END) AS npl_loan_count
FROM loan_monthly m
JOIN loans l ON l.loan_id = m.loan_id
JOIN borrowers b ON b.borrower_id = l.borrower_id
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4;

-- Per-borrower composite metrics (input of scoring engine).
-- AS-OF: last 12 months of payments, no data after 2026-08-31.
CREATE OR REPLACE VIEW v_borrower_metrics AS
WITH active_loans AS (
    SELECT * FROM loans WHERE status = 'ACTIVE'
),
loan_dpd AS (
    SELECT loan_id, dpd, outstanding_amount
    FROM loan_monthly lmn
    WHERE as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
),
per_loan AS (
    SELECT
        l.borrower_id,
        COUNT(*) AS n_active_loans,
        COALESCE(SUM(l.outstanding_amount), 0) AS total_outstanding,
        COALESCE(MAX(d.dpd), 0) AS max_dpd,
        COALESCE(MAX(d.outstanding_amount), 0) AS dpd_exposure,
        COUNT(DISTINCT l.institution_id) AS n_institutions
    FROM active_loans l
    LEFT JOIN loan_dpd d ON d.loan_id = l.loan_id
    GROUP BY l.borrower_id
),
defaults AS (
    SELECT l.borrower_id,
           COUNT(*) FILTER (WHERE l.status IN ('DEFAULTED', 'WRITTEN_OFF')) AS n_defaults,
           COUNT(*) FILTER (WHERE l.restructured_flag) AS restructured_loans,
           COUNT(*) FILTER (WHERE l.status = 'ACTIVE' AND l.start_date >= CURRENT_DATE - INTERVAL '6 months') AS n_recent_loans
    FROM loans l
    GROUP BY l.borrower_id
),
pay12 AS (
    SELECT l.borrower_id,
           SUM(CASE WHEN p.due_date <= CURRENT_DATE AND p.due_date >= CURRENT_DATE - INTERVAL '12 months'
                    THEN p.amount_paid ELSE 0 END)::float
           / NULLIF(SUM(CASE WHEN p.due_date <= CURRENT_DATE AND p.due_date >= CURRENT_DATE - INTERVAL '12 months'
                             THEN p.amount_due ELSE 0 END), 0) AS paid_ratio_12m
    FROM loans l JOIN payments p ON p.loan_id = l.loan_id
    GROUP BY l.borrower_id
),
enq AS (
    SELECT borrower_id, COUNT(*) AS n_enquiries
    FROM enquiries
    WHERE enquiry_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY borrower_id
)
SELECT
    b.borrower_id,
    COALESCE(per_loan.n_active_loans, 0) AS n_active_loans,
    COALESCE(per_loan.total_outstanding, 0) AS total_outstanding,
    COALESCE(per_loan.max_dpd, 0) AS max_dpd,
    COALESCE(per_loan.n_institutions, 0) AS n_institutions,
    COALESCE(defaults.n_defaults, 0) AS n_defaults,
    COALESCE(defaults.restructured_loans, 0) AS restructured_loans,
    COALESCE(defaults.n_recent_loans, 0) AS n_recent_loans,
    COALESCE(pay12.paid_ratio_12m, 1.0) AS paid_ratio_12m,
    COALESCE(enq.n_enquiries, 0) AS n_enquiries
FROM borrowers b
LEFT JOIN per_loan ON per_loan.borrower_id = b.borrower_id
LEFT JOIN defaults ON defaults.borrower_id = b.borrower_id
LEFT JOIN pay12 ON pay12.borrower_id = b.borrower_id
LEFT JOIN enq ON enq.borrower_id = b.borrower_id;
