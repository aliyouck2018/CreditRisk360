"""Stress-test simulator (W2). Analytic shock model documented on the page."""
from flask import Blueprint, render_template

from app.services.db import query

simulator_bp = Blueprint("simulator", __name__)

LGD = 0.55  # loss given default assumption


def base_state():
    base = query(
        """
        SELECT
            COALESCE(SUM(CASE WHEN l.status = 'ACTIVE' THEN l.outstanding_amount END), 0)::float AS exposure,
            COALESCE(SUM(CASE WHEN l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') AND lm.dpd >= 90
                              THEN l.outstanding_amount END), 0)::float AS npl
        FROM loans l
        LEFT JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        """,
        one=True)
    performing = base["exposure"] - base["npl"]
    # performing PD proxy = 12m default rate
    dr = query(
        """
        WITH active_12m AS (SELECT DISTINCT loan_id FROM loan_monthly
                            WHERE as_of_date < CURRENT_DATE - INTERVAL '1 year'),
        crossed AS (SELECT DISTINCT loan_id FROM loan_monthly
                    WHERE as_of_date >= CURRENT_DATE - INTERVAL '1 year' AND dpd >= 90)
        SELECT COALESCE((SELECT COUNT(*) FROM crossed WHERE loan_id IN (SELECT loan_id FROM active_12m))::float
                        / NULLIF((SELECT COUNT(DISTINCT loan_id) FROM active_12m), 0), 0.0) AS pd
        """,
        one=True)
    sector = query(
        """
        SELECT b.sector, SUM(l.outstanding_amount)::float AS exposure
        FROM loans l JOIN borrowers b USING (borrower_id)
        WHERE l.status = 'ACTIVE' GROUP BY 1 ORDER BY 2 DESC
        """)
    return {
        "exposure": base["exposure"],
        "npl": base["npl"],
        "pd_performing": float(dr["pd"] or 0.02),
        "sectors": sector,
    }


@simulator_bp.route("/")
def index():
    s = base_state()
    return render_template(
        "simulator/index.html",
        exposure=s["exposure"],
        npl=s["npl"],
        pd_performing=s["pd_performing"],
        sectors=[r["sector"] for r in s["sectors"]],
        lgd=LGD,
    )
