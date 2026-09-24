# CreditRisk360

CEMAC Credit Intelligence & Risk Analytics Platform — Flask + PostgreSQL (Supabase-compatible), 100% synthetic data as of **2026-08-31**.

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Database (any Postgres 14+; local by default, Supabase-compatible)
createdb -U postgres creditrisk360   # or use an existing Supabase DSN
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/creditrisk360

psql -d creditrisk360 -f schema.sql      # tables + v_* business views
python seed_supabase.py --dsn $DATABASE_URL   # deterministic seed (42): 12k borrowers, 20k loans, ~400k payments

python run.py   # http://localhost:5000
```

Tests: `.venv/bin/python -m pytest tests/ -q`

## Modules

| Route | Module |
|---|---|
| `/dashboard` | M1 — Executive KPIs + charts (ApexCharts) |
| `/borrowers` | M2 — Borrower 360° (score explicable, 36-month payment ribbon, PDF export) |
| `/risk` | M3 — DPD buckets, vintage cohort curves + heatmap, HHI, regulatory limits |
| `/data-quality` | M4 — 10 automated rules DQ-01..DQ-10, 4-dimension score, resolution workflow |
| `/alerts` | M5 — Early-Warning System (SAP) with driver attribution ("Pourquoi ?") |
| `/scoring` | W1 — Explainable scorecard (Score = 300 + 550 × Σ wᵢ·sᵢ) |
| `/simulator` | W2 — Stress-test simulator (default/rate/sector shocks, live API) |
| `/analyst` | W3 — NL→SQL analyst; SELECT-only, v_* views only, LIMIT 500 enforced |

Key files: `schema.sql` (tables + business views), `seed_supabase.py` (seed + scenarios S1/S2/S3 + planted DQ anomalies), `app/metrics.py` (canonical definitions), `app/services/scoring.py`, `app/services/dq.py`, `app/services/ai_analyst.py`, `app/services/pdf_report.py` (ReportLab A4 reports).

See `cahier_des_charges_creditrisk360.md` for the full functional specification.
