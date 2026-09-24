"""Central metrics engine — canonical business definitions.

All figures displayed in the UI must come from this module or SQL views.
Reference date: config.AS_OF_DATE (2026-08-31), nothing beyond.
"""
from datetime import date

from flask import current_app

from app.services.db import query


def as_of_date() -> date:
    return current_app.config["AS_OF_DATE"]


# ---------------------------------------------------------------
# Core portfolio KPIs
# ---------------------------------------------------------------

def kpi_summary():
    """One-pass executive summary."""
    as_of = as_of_date()
    row = query(
        """
        SELECT
            (SELECT COALESCE(SUM(outstanding_amount), 0) FROM loans WHERE status = 'ACTIVE') AS exposure,
            (SELECT COUNT(*) FROM borrowers) AS borrower_count,
            (SELECT COUNT(*) FROM loans WHERE status = 'ACTIVE') AS active_loan_count,
            (SELECT COUNT(*) FROM loans WHERE status = 'CLOSED') AS closed_loan_count,
            (SELECT COUNT(*) FROM loans WHERE status IN ('DEFAULTED', 'WRITTEN_OFF')) AS defaulted_loan_count,
            (SELECT COALESCE(SUM(l.outstanding_amount), 0)
             FROM loans l
             JOIN loan_monthly m2 ON m2.loan_id = l.loan_id
                 AND m2.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
             WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') AND m2.dpd >= 90
            ) AS npl_outstanding
        """,
        {"as_of": as_of},
        one=True,
    )
    exposure = float(row["exposure"])
    npl_outstanding = float(row["npl_outstanding"])
    npl_ratio = npl_outstanding / exposure * 100 if exposure else 0.0

    # 12-month default rate: loans that crossed >=90 DPD in last 12m / active 12m ago
    d12 = as_of.replace(year=as_of.year - 1)
    dr = query(
        """
        WITH active_12m AS (SELECT DISTINCT loan_id FROM loan_monthly WHERE as_of_date <= %(d12)s),
        crossed AS (SELECT DISTINCT loan_id FROM loan_monthly
                    WHERE as_of_date > %(d12)s AND as_of_date <= %(as_of)s AND dpd >= 90)
        SELECT
            (SELECT COUNT(*) FROM crossed WHERE loan_id IN (SELECT loan_id FROM active_12m))::float
            / NULLIF((SELECT COUNT(DISTINCT loan_id) FROM active_12m), 0) * 100 AS default_rate_12m
        """,
        {"d12": d12, "as_of": as_of},
        one=True,
    )
    default_rate_12m = float(dr["default_rate_12m"] or 0)

    # Payment rate: paid / due as of reference date
    pay = query(
        """
        SELECT
            COALESCE(SUM(CASE WHEN due_date <= %(as_of)s THEN amount_paid ELSE 0 END), 0) AS paid,
            COALESCE(SUM(CASE WHEN due_date <= %(as_of)s THEN amount_due ELSE 0 END), 0) AS due
        FROM payments
        WHERE loan_id IN (SELECT loan_id FROM loans WHERE status IN ('ACTIVE', 'CLOSED', 'DEFAULTED'))
        """,
        {"as_of": as_of},
        one=True,
    )
    due_total = float(pay["due"])
    payment_rate = float(pay["paid"]) / due_total * 100 if due_total else 0.0

    return {
        "exposure": exposure,
        "borrower_count": row["borrower_count"],
        "active_loan_count": row["active_loan_count"],
        "closed_loan_count": row["closed_loan_count"],
        "defaulted_loan_count": row["defaulted_loan_count"],
        "npl_outstanding": npl_outstanding,
        "npl_ratio": npl_ratio,
        "default_rate_12m": default_rate_12m,
        "payment_rate": payment_rate,
    }


def borrower_metrics(borrower_id):
    """Per-borrower aggregates used by scoring and 360° view."""
    return query(
        "SELECT * FROM v_borrower_metrics WHERE borrower_id = %(bid)s",
        {"bid": borrower_id},
        one=True,
    )


# ---------------------------------------------------------------
# Chart data
# ---------------------------------------------------------------

def monthly_trend(months=24):
    """Exposure + NPL evolution over the last N months."""
    rows = query(
        """
        SELECT to_char(as_of_month, 'MM/YYYY') AS m,
               total_outstanding, npl_outstanding, npl_ratio
        FROM v_kpi_monthly
        ORDER BY as_of_month
        """,
    )
    rows = rows[-months:]
    return {
        "labels": [r["m"] for r in rows],
        "exposure": [round(float(r["total_outstanding"]) / 1e9, 2) for r in rows],
        "npl": [round(float(r["npl_outstanding"]) / 1e9, 2) for r in rows],
        "npl_ratio": [round(float(r["npl_ratio"]), 2) for r in rows],
    }


def exposure_by_country():
    rows = query(
        """
        SELECT COALESCE(c.name_short_fr, 'Inconnu') AS country,
               COALESCE(SUM(l.outstanding_amount), 0) AS exposure
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        WHERE l.status = 'ACTIVE'
        GROUP BY 1
        ORDER BY 2 DESC
        """,
    )
    return [{"name": r["country"], "value": float(r["exposure"])} for r in rows]


def exposure_by_sector():
    rows = query(
        """
        SELECT b.sector, COALESCE(SUM(l.outstanding_amount), 0) AS exposure
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        WHERE l.status = 'ACTIVE'
        GROUP BY 1
        ORDER BY 2 DESC
        """,
    )
    return [{"name": r["sector"], "value": float(r["exposure"])} for r in rows]


def risk_band_distribution(limit=800):
    """Distribution of active borrowers across risk bands (scored sample)."""
    from app.services.scoring import score_borrower_row
    rows = query(
        f"""
        SELECT DISTINCT ON (b.borrower_id)
               b.borrower_id, b.display_name, b.borrower_type, b.country, b.sector,
               m.total_outstanding, m.max_dpd, m.n_active_loans, m.n_institutions,
               m.n_defaults, m.restructured_loans, m.paid_ratio_12m
        FROM borrowers b
        JOIN loans l ON l.borrower_id = b.borrower_id AND l.status = 'ACTIVE'
        LEFT JOIN v_borrower_metrics m ON m.borrower_id = b.borrower_id
        ORDER BY b.borrower_id
        LIMIT %(limit)s
        """,
        {"limit": limit},
    )
    counts = {"Faible": 0, "Modéré": 0, "Élevé": 0, "Très Élevé": 0}
    for b in rows:
        s = score_borrower_row(b)
        counts[s["risk_band"]] = counts.get(s["risk_band"], 0) + 1
    return [{"name": k, "value": v} for k, v in counts.items() if v > 0]
