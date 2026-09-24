"""Data Quality engine: 10 automated rules (DQ-01..DQ-10) + 4 dimension scores.

Rule statuses are persisted in app_state_dq_resolutions; the workflow allows
marking issues INVESTIGATING / RESOLVED, with optional automated fixes for
simple violation classes.
"""
from flask import current_app
from datetime import timedelta

from app.metrics import as_of_date
from app.services.db import execute, query

RULES = [
    {
        "id": "DQ-01", "dimension": "Complétude",
        "label_fr": "Dates manquantes (octroi / échéance)",
        "sql": ("SELECT l.loan_id, b.display_name, l.status, l.outstanding_amount "
                "FROM loans l JOIN borrowers b USING (borrower_id) "
                "WHERE l.start_date IS NULL OR l.maturity_date IS NULL OR l.interest_rate IS NULL LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loans WHERE start_date IS NULL OR maturity_date IS NULL OR interest_rate IS NULL",
    },
    {
        "id": "DQ-02", "dimension": "Unicité",
        "label_fr": "Doublons d'emprunteurs (même profil)",
        "sql": ("SELECT b.display_name, b.borrower_type, b.sector, c.name_short_fr AS country, COUNT(*) AS n "
                "FROM borrowers b LEFT JOIN countries c ON c.country_code = b.country "
                "GROUP BY b.display_name, b.borrower_type, b.sector, b.country, c.name_short_fr "
                "HAVING COUNT(*) > 1 ORDER BY n DESC LIMIT 50"),
        "count_sql": ("SELECT COALESCE(SUM(n), 0) AS n FROM ("
                      "SELECT COUNT(*) AS n FROM borrowers b GROUP BY b.display_name, b.borrower_type, b.sector, b.country "
                      "HAVING COUNT(*) > 1) d"),
    },
    {
        "id": "DQ-03", "dimension": "Validité",
        "label_fr": "Encours négatifs",
        "sql": ("SELECT l.loan_id, b.display_name, l.outstanding_amount, l.status "
                "FROM loans l JOIN borrowers b USING (borrower_id) WHERE l.outstanding_amount < 0 LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loans WHERE outstanding_amount < 0",
    },
    {
        "id": "DQ-04", "dimension": "Validité",
        "label_fr": "Échéance antérieure à la date d'octroi",
        "sql": ("SELECT l.loan_id, b.display_name, l.start_date, l.maturity_date "
                "FROM loans l JOIN borrowers b USING (borrower_id) "
                "WHERE l.start_date IS NOT NULL AND l.maturity_date IS NOT NULL AND l.maturity_date < l.start_date LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loans WHERE start_date IS NOT NULL AND maturity_date IS NOT NULL AND maturity_date < start_date",
    },
    {
        "id": "DQ-05", "dimension": "Cohérence",
        "label_fr": "Prêts CLOSED avec encours résiduel",
        "sql": ("SELECT l.loan_id, b.display_name, l.outstanding_amount "
                "FROM loans l JOIN borrowers b USING (borrower_id) "
                "WHERE l.status = 'CLOSED' AND l.outstanding_amount <> 0 LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loans WHERE status = 'CLOSED' AND outstanding_amount <> 0",
    },
    {
        "id": "DQ-06", "dimension": "Validité",
        "label_fr": "DPD incohérent (bucket CURRENT avec DPD > 0)",
        "sql": ("SELECT loan_id, as_of_date, dpd, dpd_bucket FROM loan_monthly "
                "WHERE (dpd_bucket = 'CURRENT' AND dpd > 0) "
                "   OR (dpd_bucket = '90+' AND dpd < 90) LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loan_monthly WHERE (dpd_bucket = 'CURRENT' AND dpd > 0) OR (dpd_bucket = '90+' AND dpd < 90)",
    },
    {
        "id": "DQ-07", "dimension": "Cohérence",
        "label_fr": "Paiements postérieurs à la date de référence",
        "sql": ("SELECT p.payment_id, l.loan_id, p.due_date, p.payment_date "
                "FROM payments p JOIN loans l USING (loan_id) "
                "WHERE p.payment_date > %(as_of)s LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM payments WHERE payment_date > %(as_of)s",
    },
    {
        "id": "DQ-08", "dimension": "Validité",
        "label_fr": "Taux d'intérêt hors plage [1 %, 25 %]",
        "sql": ("SELECT loan_id, interest_rate, status FROM loans "
                "WHERE interest_rate < 1 OR interest_rate > 25 LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM loans WHERE interest_rate < 1 OR interest_rate > 25",
    },
    {
        "id": "DQ-09", "dimension": "Complétude",
        "label_fr": "Champs d'emprunteur manquants (pays / date d'inscription)",
        "sql": ("SELECT borrower_id, display_name, country, registration_date "
                "FROM borrowers WHERE country IS NULL OR registration_date IS NULL LIMIT 100"),
        "count_sql": "SELECT COUNT(*) AS n FROM borrowers WHERE country IS NULL OR registration_date IS NULL",
    },
    {
        "id": "DQ-10", "dimension": "Cohérence",
        "label_fr": "Chronologie incohérente (octroi antérieur à l'inscription)",
        "sql": ("SELECT l.loan_id, b.display_name, b.registration_date, l.start_date "
                "FROM loans l JOIN borrowers b USING (borrower_id) "
                "WHERE b.registration_date IS NOT NULL AND b.borrower_id IN "
                "  (SELECT borrower_id FROM borrowers WHERE registration_date IS NOT NULL) "
                "AND l.start_date < b.registration_date AND b.borrower_id IN (SELECT borrower_id FROM borrowers WHERE borrower_id = borrowers.borrower_id) LIMIT 100"),
        "count_sql": None,  # computed programmatically (self-reference caveat)
    },
]

RULE_BY_ID = {r["id"]: r for r in RULES}

# Rules automatically fixable by the workflow
FIXABLE = sorted({"DQ-03", "DQ-04", "DQ-05", "DQ-07", "DQ-08"})


def run_all():
    """Run every rule → list of dicts with issue counts + per-dimension scores."""
    as_of = as_of_date()
    results = []
    for rule in RULES:
        if rule["count_sql"] is None:
            n = query(
                """
                SELECT COUNT(*) AS n
                FROM loans l JOIN borrowers b USING (borrower_id)
                WHERE b.registration_date IS NOT NULL AND b.borrower_id = l.borrower_id
                  AND l.start_date IS NOT NULL AND l.start_date < b.registration_date
                """,
                one=True)["n"]
        else:
            n = query(rule["count_sql"], {"as_of": as_of}, one=True)["n"]
        rule_score = max(0, 100 - min(100, 2 * n)) if n else 100
        results.append({**rule, "count": n, "score": rule_score})

    dims = {}
    for r in results:
        dims.setdefault(r["dimension"], []).append(r["score"])
    dim_scores = {k: round(sum(v) / len(v), 1) for k, v in dims.items()}
    global_score = round(sum(dim_scores.values()) / len(dim_scores), 1)
    return results, dim_scores, global_score


def rule_records(rule_id):
    rule = RULE_BY_ID[rule_id]
    return query(rule["sql"], {"as_of": as_of_date()}), rule


def issues_state(issue_ids=None):
    if issue_ids:
        rows = query(
            "SELECT issue_id, status FROM app_state_dq_resolutions WHERE issue_id = ANY(%(ids)s)",
            {"ids": list(issue_ids)})
        return {r["issue_id"]: r["status"] for r in rows}
    rows = query("SELECT issue_id, status FROM app_state_dq_resolutions")
    return {r["issue_id"]: r["status"] for r in rows}


def set_status(issue, rule_id, record_id, status):
    current_app.logger.info("DQ workflow: %s %s -> %s", rule_id, record_id, status)
    execute(
        """
        INSERT INTO app_state_dq_resolutions (issue_id, rule_id, record_id, status, updated_at)
        VALUES (%(iid)s, %(rid)s, %(rec)s, %(st)s, CURRENT_TIMESTAMP)
        ON CONFLICT (issue_id) DO UPDATE
          SET status = %(st)s, updated_at = CURRENT_TIMESTAMP
        """,
        {"iid": issue, "rid": rule_id, "rec": record_id, "st": status})


def issue_id(rule_id, record_id):
    return f"{rule_id}:{record_id}"


def apply_fix(rule_id, record_id):
    """Auto-fix a single violation (simple, safe transformations)."""
    if rule_id == "DQ-03":
        execute("UPDATE loans SET outstanding_amount = ABS(outstanding_amount) WHERE loan_id = %(r)s", {"r": record_id})
    elif rule_id == "DQ-04":
        execute("UPDATE loans SET maturity_date = start_date + INTERVAL '5 years' WHERE loan_id = %(r)s", {"r": record_id})
    elif rule_id == "DQ-05":
        execute("UPDATE loans SET outstanding_amount = 0 WHERE loan_id = %(r)s", {"r": record_id})
    elif rule_id == "DQ-07":
        execute("UPDATE payments SET payment_date = LEAST(payment_date, %(as_of)s) WHERE payment_id = %(r)s::bigint",
                {"r": record_id, "as_of": as_of_date()})
    elif rule_id == "DQ-08":
        execute("""
            UPDATE loans SET interest_rate = LEAST(GREATEST(interest_rate, 1.0), 25.0)
            WHERE loan_id = %(r)s
            AND (interest_rate < 0 OR interest_rate > 100)
        """, {"r": record_id})
        execute("""
            UPDATE loans SET interest_rate = CASE WHEN interest_rate <= 0 THEN 6.5 ELSE LEAST(interest_rate, 18.0) END
            WHERE loan_id = %(r)s
        """, {"r": record_id})
    else:
        raise ValueError(f"Rule {rule_id} is not auto-fixable")
