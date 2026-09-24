from flask import Blueprint, current_app, render_template

from app.metrics import as_of_date
from app.services.db import query

risk_bp = Blueprint("risk", __name__)

BREAKPOINTS = {
    "CURRENT": ("Courant", "badge-green-bg", "badge-green-fg"),
    "1-30": ("Retard 1-30 j", "badge-amber-bg", "badge-amber-fg"),
    "31-60": ("Retard 31-60 j", "badge-amber-bg", "badge-amber-fg"),
    "61-90": ("Retard 61-90 j", "badge-red-bg", "badge-red-fg"),
    "90+": ("Défaut 90+ j", "badge-red-bg", "badge-red-fg"),
}

COHORT_ORDER = [f"{y} T{q}" for y in (2023, 2024, 2025, 2026) for q in (1, 2, 3, 4)]


def dpd_distribution():
    as_of = as_of_date()
    rows = query(
        """
        SELECT dpd_bucket, COUNT(*) AS n, SUM(outstanding_amount) AS exposure
        FROM loan_monthly WHERE as_of_date = %(as_of)s
        GROUP BY 1
        """,
        {"as_of": as_of})
    order = ["CURRENT", "1-30", "31-60", "61-90", "90+"]
    dpd_map = {r["dpd_bucket"]: r for r in rows}
    return [{**dpd_map[b], "bucket": b,
             "label": BREAKPOINTS[b][0], "bg": BREAKPOINTS[b][1], "fg": BREAKPOINTS[b][2]}
            for b in order if b in dpd_map]


def vintage_curves(max_mob=23):
    """Cumulative 90dpd default % per quarterly cohort by month-on-book."""
    loans = query(
        """
        SELECT l.loan_id, to_char(l.start_date, 'YYYY" T"Q') AS cohort,
               (DATE_PART('year', l.start_date)::int * 12 + DATE_PART('month', l.start_date)::int) AS start_m
        FROM loans l
        WHERE l.start_date >= '2023-01-01'
              AND l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF')
        """)
    defs = query(
        """
        SELECT l.loan_id,
               MIN(DATE_PART('year', m.as_of_date)::int * 12 + DATE_PART('month', m.as_of_date)::int) AS def_m
        FROM loan_monthly m JOIN loans l USING (loan_id)
        WHERE l.start_date >= '2023-01-01' AND m.dpd >= 90
        GROUP BY 1
        """)
    start_m = {l["loan_id"]: int(l["start_m"]) for l in loans}
    cohort_of = {l["loan_id"]: l["cohort"] for l in loans}
    first_def_mob = {}
    for r in defs:
        if r["loan_id"] not in start_m:
            continue
        first_def_mob[r["loan_id"]] = int(r["def_m"]) - start_m[r["loan_id"]]

    cohorts = {}
    for lid, co in cohort_of.items():
        cohorts.setdefault(co, []).append(lid)
    # observation limit per cohort: loan_monthly only starts 2024-09; MOB is
    # computed in loan time so old cohorts start their curve at their first
    # observable month, which is acceptable for a synthetic dataset.
    curves = []
    for co in COHORT_ORDER:
        ids = cohorts.get(co, [])
        if not ids:
            continue
        cum = []
        for mob in range(0, max_mob + 1):
            n_def = sum(1 for i in ids if i in first_def_mob and first_def_mob[i] <= mob)
            cum.append(round(n_def / len(ids) * 100, 2))
        curves.append({"cohort": co, "vals": cum, "size": len(ids)})
    return curves


@risk_bp.route("/")
def index():
    dpd = dpd_distribution()
    curves = vintage_curves()
    total_exposure = query(
        "SELECT COALESCE(SUM(outstanding_amount),0) AS e FROM loans WHERE status = 'ACTIVE'", one=True)["e"]

    # HHI by sector / country
    sector_rows = query(
        """
        SELECT b.sector, SUM(l.outstanding_amount) AS exposure
        FROM loans l JOIN borrowers b USING (borrower_id)
        WHERE l.status = 'ACTIVE' GROUP BY 1 ORDER BY 2 DESC
        """)
    country_rows = query(
        """
        SELECT b.country, SUM(l.outstanding_amount) AS exposure
        FROM loans l JOIN borrowers b USING (borrower_id)
        WHERE l.status = 'ACTIVE' GROUP BY 1 ORDER BY 2 DESC
        """)

    def hhi(rows):
        s = sum(r["exposure"] for r in rows) or 1
        return round(sum((r["exposure"] / s) ** 2 for r in rows) * 10_000, 1)

    hhi_sector = hhi(sector_rows)
    hhi_country = hhi(country_rows)

    # concentration limits: sector <= 25% of country exposure
    sector_limits = query(
        """
        SELECT c.name_short_fr AS country, b.sector, SUM(l.outstanding_amount) AS exposure
        FROM loans l JOIN borrowers b USING (borrower_id)
        JOIN countries c ON c.country_code = b.country
        WHERE l.status = 'ACTIVE'
        GROUP BY 1, 2 ORDER BY 3 DESC
        """)
    country_expo = {}
    for r in sector_limits:
        country_expo[r["country"]] = country_expo.get(r["country"], 0) + r["exposure"]

    limit_rows = []
    for r in sector_limits[:30]:
        share = (r["exposure"] / country_expo.get(r["country"], 1)) * 100
        limit_rows.append({**r, "share": round(share, 1),
                           "status": "DÉPASSEMENT" if share > 25 else ("VIGILANCE" if share > 20 else "OK")})

    borrower_limits = query(
        """
        SELECT b.display_name, c.name_short_fr AS country, SUM(l.outstanding_amount) AS exposure
        FROM loans l JOIN borrowers b USING (borrower_id)
        JOIN countries c ON c.country_code = b.country
        WHERE l.status = 'ACTIVE' AND b.display_name IS NOT NULL
        GROUP BY 1, 2 HAVING SUM(l.outstanding_amount) > %(min)s
        ORDER BY 3 DESC LIMIT 15
        """,
        {"min": total_exposure * 0.012})
    borrower_rows = []
    for r in borrower_limits:
        share = r["exposure"] / total_exposure * 100
        borrower_rows.append({**r, "share": round(share, 2),
                              "status": "DÉPASSEMENT" if share > 2 else ("VIGILANCE" if share > 1.6 else "OK")})

    import json

    vintage_series = [{"name": c["cohort"], "data": c["vals"]} for c in curves]
    vintage_x = list(range(0, 24))

    return render_template("risk/index.html",
                           dpd=dpd,
                           curves=curves,
                           hhi_sector=hhi_sector,
                           hhi_country=hhi_country,
                           sector_limits=limit_rows,
                           borrower_limits=borrower_rows,
                           sector_limit_pct=current_app.config["SECTOR_CONCENTRATION_LIMIT"],
                           borrower_limit_pct=current_app.config["SINGLE_BORROWER_LIMIT"],
                           total_exposure=total_exposure,
                           dpd_values_json=json.dumps(
                               [round(r["exposure"] / 1e9, 2) for r in dpd]),
                           dpd_labels_json=json.dumps([r["label"] for r in dpd]),
                           vintage_series_json=json.dumps(vintage_series),
                           vintage_x_json=json.dumps(vintage_x),
                           hhi_series_json=json.dumps(
                               [{"name": r["sector"],
                                 "y": round(r["exposure"] / total_exposure * 100, 2)}
                                for r in sector_rows[:8]]))
