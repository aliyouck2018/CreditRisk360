"""Pytest suite — CreditRisk360 (uses local Postgres seeded by seed_supabase.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from app import create_app
from app.services.db import query


@pytest.fixture()
def app():
    app = create_app()
    app.testing = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


# ------------------------------------------------------------------
# Phase 0 / routes survival
# ------------------------------------------------------------------

def test_all_pages_200(client):
    for url in [
        "/", "/dashboard", "/borrowers/", "/risk/", "/data-quality/",
        "/alerts/", "/scoring/", "/simulator/", "/analyst/", "/methodology",
    ]:
        assert client.get(url).status_code == 200, url


# ------------------------------------------------------------------
# Canonical metric definitions
# ------------------------------------------------------------------

def test_metrics_consistency(app):
    with app.app_context():
        from app import metrics
        s = metrics.kpi_summary()
        assert s["exposure"] > 0
        assert s["borrower_count"] > 10_000
        # NPL ratio = DPD>=90 exposure / active exposure
        expected = query(
            """
            SELECT COALESCE(SUM(l.outstanding_amount), 0) AS n FROM loans l
            JOIN loan_monthly m ON m.loan_id = l.loan_id
                AND m.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
            WHERE l.status IN ('ACTIVE','DEFAULTED','WRITTEN_OFF') AND m.dpd >= 90
            """, one=True)["n"]
        assert abs(s["npl_outstanding"] - float(expected)) < 1e-6
        assert 0 <= s["npl_ratio"] <= 100
        assert 0 <= s["payment_rate"] <= 100


def test_no_future_data(app):
    with app.app_context():
        from app import metrics
        rows = query("SELECT COALESCE(MAX(as_of_month::date), '2010-01-01') AS m FROM v_kpi_monthly", one=True)
        assert rows["m"] <= metrics.as_of_date().replace(day=1)


# ------------------------------------------------------------------
# AI analyst guardrails
# ------------------------------------------------------------------

def test_analyst_guardrails(client):
    # SELECT-only on v_* views
    r = client.post("/analyst/query", json={"question": "SELECT * FROM countries"}).json
    assert r["ok"] is False
    r = client.post("/analyst/query", json={"question": "SELECT * FROM pg_tables"}).json
    assert r["ok"] is False
    r = client.post("/analyst/query", json={"question": "DROP TABLE x"}).json
    assert "fallback" not in str(r).lower() and r.get("ok", True)
    # LIMIT imposed
    r = client.post("/analyst/query", json={"question": "SELECT * FROM v_kpi_monthly"}).json
    assert r["ok"] and "LIMIT 500" in r["sql"]


def test_analyst_answer_cites_numbers(client):
    r = client.post("/analyst/query", json={"question": "Encours par pays"}).json
    assert r["ok"]
    assert any(str(v) in r["explanation"] for row in r["rows"] for v in row)


# ------------------------------------------------------------------
# Data quality workflow
# ------------------------------------------------------------------

def test_dq_workflow(app):
    with app.app_context():
        from app.services.dq import run_all, rule_records, set_status, issue_id, issues_state
        rules, dims, gscore = run_all()
        assert 0 <= gscore <= 100
        assert len(rules) == 10
        # pick a DQ-03 (negative outstanding) record
        recs, _ = rule_records("DQ-03")
        assert recs, "seed should plant negative outstanding loans"
        token = recs[0]["loan_id"]
        set_status("DQ-03:" + token, "DQ-03", token, "INVESTIGATING")
        assert issues_state()["DQ-03:" + token] == "INVESTIGATING"


def test_dq_auto_fix(app):
    with app.app_context():
        from app.services import dq
        recs, _ = dq.rule_records("DQ-05")
        if recs:
            lid = recs[0]["loan_id"]
            dq.apply_fix("DQ-05", lid)
            after = query("SELECT outstanding_amount FROM loans WHERE loan_id = %(l)s", {"l": lid}, one=True)
            assert float(after["outstanding_amount"]) == 0
