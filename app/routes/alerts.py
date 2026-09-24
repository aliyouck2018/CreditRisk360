"""SAP / Early-Warning System: segment drift detection with driver attribution."""
import calendar
from datetime import date

from flask import Blueprint, render_template

from app.services.db import query

alerts_bp = Blueprint("alerts", __name__)


def shift_months(d: date, n: int) -> date:
    """Return the 1st of the month n months from d."""
    total = d.year * 12 + d.month - 1 + n
    return date(total // 12, total % 12 + 1, 1)


def segment_rows(month_start):
    return query(
        """
        SELECT COALESCE(country, 'N/D') AS country, COALESCE(sector, 'N/D') AS sector,
               COALESCE(borrower_type, 'N/D') AS borrower_type, total_outstanding, npl_outstanding
        FROM (
            SELECT b.country, b.sector, b.borrower_type, SUM(m.outstanding_amount) AS total_outstanding,
                   SUM(CASE WHEN m.dpd >= 90 THEN m.outstanding_amount ELSE 0 END) AS npl_outstanding
            FROM loan_monthly m JOIN loans l USING (loan_id) JOIN borrowers b USING (borrower_id)
            WHERE date_trunc('month', m.as_of_date) = %(m)s
            GROUP BY 1, 2, 3
        ) seg
        """,
        {"m": month_start})


def _drivers(country, sector, npl_total, as_of):
    """Why is this segment deteriorating? Share attribution of 90+ exposure."""
    if npl_total <= 0:
        return []
    rows = query(
        """
        SELECT
            SUM(CASE WHEN l.start_date >= date_trunc('month', %(d6m)s::date)
                     THEN d.outstanding_amount ELSE 0 END)::float AS new_loans_npl,
            SUM(CASE WHEN l.restructured_flag
                     THEN d.outstanding_amount ELSE 0 END)::float AS restructured_npl,
            SUM(CASE WHEN NOT l.restructured_flag
                      AND l.start_date < date_trunc('month', %(d6m)s::date)
                     THEN d.outstanding_amount ELSE 0 END)::float AS structural_npl
        FROM loan_monthly d
        JOIN loans l USING (loan_id)
        JOIN borrowers b USING (borrower_id)
        WHERE d.as_of_date = %(as_of)s AND d.dpd >= 90
          AND b.country = %(country)s AND b.sector = %(sector)s
        """,
        {"as_of": as_of, "d6m": shift_months(as_of, -6),
         "country": country, "sector": sector},
        one=True)
    if not rows:
        return []
    parts = [
        ("Dérive des nouveaux prêts < 6 mois", rows["new_loans_npl"], "#DC2626"),
        ("Prêts restructurés en défaut", rows["restructured_npl"], "#D97706"),
        ("Structurés / anciens (détérioration progressive)", rows["structural_npl"], "#0284C7"),
    ]
    drivers = []
    for label, amount, color in parts:
        if amount and amount > 0:
            drivers.append({"label": label, "amount": amount,
                            "pct": round(amount / npl_total * 100, 1), "color": color})
    drivers.sort(key=lambda d: -d["pct"])
    return drivers


@alerts_bp.route("/")
def index():
    as_of_months = query(
        "SELECT DISTINCT as_of_month FROM v_segment_monthly ORDER BY 1 DESC LIMIT 2")
    if len(as_of_months) < 1:
        return render_template("alerts/index.html", alerts=[])
    current = as_of_months[0]["as_of_month"]
    before = as_of_months[1]["as_of_month"] if len(as_of_months) > 1 else current

    now = {r["country"] + "|" + r["sector"] + "|" + r["borrower_type"]: r
           for r in segment_rows(current)}
    before = {r["country"] + "|" + r["sector"] + "|" + r["borrower_type"]: r
              for r in segment_rows(before)}

    alerts = []
    for k, s in now.items():
        exposure = s["total_outstanding"] or 0
        npl = s["npl_outstanding"] or 0
        npl_ratio = npl / exposure * 100 if exposure else 0
        b = before.get(k)
        b_ratio = (b["npl_outstanding"] / b["total_outstanding"] * 100) if (b and b["total_outstanding"]) else 0
        drift = npl_ratio - b_ratio
        if npl_ratio < 8 and drift < 2.5:
            continue
        if npl_ratio >= 12 or drift >= 5:
            level = "HIGH"
        elif npl_ratio >= 8 or drift >= 2.5:
            level = "MEDIUM"
        else:
            continue

        country, sector, btype = k.split("|")
        alerts.append({
            "country": country, "sector": sector, "borrower_type": btype,
            "exposure": exposure, "npl": npl,
            "npl_ratio": round(npl_ratio, 1),
            "npl_ratio_before": round(b_ratio, 1),
            "drift": round(drift, 1),
            "level": level,
            "drivers": _drivers(country, sector, npl, current),
        })
    alerts.sort(key=lambda a: (a["level"] != "HIGH", -a["drift"]))
    return render_template("alerts/index.html", alerts=alerts)
