"""Dashboard analytics service (KPIs, charts, signals, observations).

All metrics respect the definitions documented on /methodology — no new
thresholds, no fabricated data. Filters (country / sector / borrower type)
applied consistently across every widget.
"""
from flask import current_app, request

from app.services.db import query

BUCKET_ORDER = ["CURRENT", "1-30", "31-60", "61-90", "90+"]

BUCKET_LABELS = {
    "CURRENT": "À jour",
    "1-30": "Retard 1-30 j",
    "31-60": "Retard 31-60 j",
    "61-90": "Retard 61-90 j",
    "90+": "Défaut 90+ j",
}


def _filters():
    country = (request.args.get("country") or "").strip()
    sector = (request.args.get("sector") or "").strip()
    btype = (request.args.get("type") or "").strip()
    try:
        months = max(6, min(24, int(request.args.get("months", 12))))
    except ValueError:
        months = 12
    return country, sector, btype, months


def _filter_params(country, sector, btype):
    clauses, params = [], {}
    if country:
        clauses.append("b.country = %(country)s")
        params["country"] = country
    if sector:
        clauses.append("b.sector = %(sector)s")
        params["sector"] = sector
    if btype:
        clauses.append("b.borrower_type = %(type)s")
        params["type"] = btype
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _latest_facts(fr_where, f_params):
    """Per-loan snapshot at last available month, respecting filters."""
    return query(
        f"""
        SELECT CASE
                 WHEN lm.dpd >= 90 THEN '90+'
                 WHEN lm.dpd >= 61 THEN '61-90'
                 WHEN lm.dpd >= 31 THEN '31-60'
                 WHEN lm.dpd >= 1  THEN '1-30'
                 ELSE 'CURRENT' END AS bucket,
               COALESCE(SUM(l.outstanding_amount), 0)::float AS exposure,
               COUNT(*) AS loans
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1
        """,
        f_params)


def get_dashboard_context():
    country, sector, btype, months = _filters()
    as_of = current_app.config["AS_OF_DATE"]
    fr_where, fr = _filter_params(country, sector, btype)

    # ------- portfolio trend (global, whole portfolio) -------
    rows = query(
        """
        SELECT to_char(as_of_month, 'MM/YYYY') AS m,
               SUM(total_outstanding)::float AS exposure,
               SUM(npl_outstanding)::float AS npl
        FROM v_segment_monthly
        GROUP BY 1
        """)
    monthly = {}
    for r in rows:
        a = monthly.setdefault(r["m"], {"exposure": 0.0, "npl": 0.0})
        a["exposure"] += r["exposure"]
        a["npl"] += r["npl"]
    mlist = sorted(monthly, key=lambda x: (x.split('/')[1], x.split('/')[0]))[-months:]
    trend = {
        "labels": mlist,
        "exposure": [round(monthly[m]["exposure"] / 1e9, 2) for m in mlist],
        "npl": [round(monthly[m]["npl"] / 1e9, 2) for m in mlist],
        "npl_ratio": [round(monthly[m]["npl"] / monthly[m]["exposure"] * 100, 2)
                      if monthly[m]["exposure"] else 0 for m in mlist],
    }

    # ------- current snapshot respecting filters -------
    dist = _latest_facts(fr_where, fr)
    bmap = {r["bucket"]: r for r in dist}
    exposure = sum(r["exposure"] for r in dist)
    npl = bmap.get("90+", {"exposure": 0.0})["exposure"]
    delinq = sum(bmap.get(b, {"exposure": 0.0})["exposure"] for b in BUCKET_ORDER[1:-1])

    pay = query(
        f"""
        SELECT COALESCE(SUM(CASE WHEN p.due_date <= CURRENT_DATE
                                  AND p.due_date >= CURRENT_DATE - INTERVAL '12 months'
                                 THEN p.amount_paid END), 0)::float AS paid,
               COALESCE(SUM(CASE WHEN p.due_date <= CURRENT_DATE
                                  AND p.due_date >= CURRENT_DATE - INTERVAL '12 months'
                                 THEN p.amount_due END), 0)::float AS due
        FROM payments p
        JOIN loans l USING (loan_id)
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        WHERE 1 = 1 {fr_where}
        """,
        fr, one=True)
    payment_rate = float(pay["paid"]) / float(pay["due"]) * 100 if float(pay["due"]) else 0.0

    prev_month = query(
        "SELECT MAX(as_of_date) AS m FROM loan_monthly WHERE as_of_date < (SELECT MAX(as_of_date) FROM loan_monthly)",
        one=True)["m"]
    prev_exposure, prev_npl = _stats_at(prev_month, fr_where, fr) if prev_month else (None, None)
    npl_ratio = npl / exposure * 100 if exposure else 0.0
    prev_npl_ratio = (prev_npl / prev_exposure * 100) if (prev_exposure and prev_npl is not None) else None

    # ------- risk by segment -------
    segments = query(
        f"""
        SELECT COALESCE(c.name_short_fr, 'N/D') AS country, b.sector,
               SUM(lm.outstanding_amount)::float AS exposure,
               SUM(CASE WHEN lm.dpd >= 90 THEN lm.outstanding_amount ELSE 0 END)::float AS npl,
               COUNT(*) AS loans
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1, 2
        ORDER BY npl DESC
        """,
        fr)
    last_months = query(
        "SELECT DISTINCT as_of_month FROM v_segment_monthly ORDER BY 1 DESC LIMIT 7")
    now_pct, before_pct = {}, {}
    if last_months:
        rels = query(
            """
            SELECT country, sector,
                   SUM(npl_outstanding)::float AS npl_sum,
                   SUM(total_outstanding)::float AS expo_sum,
                   CASE WHEN as_of_month = %(mnow)s THEN 'now'
                 WHEN as_of_month = %(mbefore)s THEN 'before' END AS side
            FROM v_segment_monthly
            WHERE as_of_month IN (%(mnow)s, %(mbefore)s) AND country IS NOT NULL AND sector IS NOT NULL
            GROUP BY 1, 2, 5
            """,
             {"mnow": last_months[0]["as_of_month"],
              "mbefore": last_months[-1]["as_of_month"]})
    for r in rels:
            bucket = now_pct if r["side"] == "now" else before_pct
            k = (r["country"], r["sector"])
            a = bucket.setdefault(k, [0.0, 0.0])
            a[0] += r["npl_sum"]
            a[1] += r["expo_sum"]

    def drift_for(c, s):
        n = now_pct.get((c, s))
        b = before_pct.get((c, s))
        if not n or not b or not b[1] or not n[1]:
            return 0.0
        return round((n[0] / n[1] - b[0] / b[1]) * 100, 1)

    top_segments = []
    for r in segments[:10]:
        top_segments.append({
            "country": r["country"], "sector": r["sector"],
            "exposure": r["exposure"], "npl": r["npl"], "loans": r["loans"],
            "npl_ratio": round(r["npl"] / (r["exposure"] or 1) * 100, 1),
            "drift": drift_for(r["country"], r["sector"]),
        })

    # ------- concentration (same definitions as /risk) -------
    sector_rows = query(
        f"""
        SELECT b.sector, SUM(lm.outstanding_amount)::float AS exposure
        FROM loans l JOIN borrowers b ON b.borrower_id = l.borrower_id
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1 ORDER BY 2 DESC
        """,
        fr)
    country_rows = query(
        f"""
        SELECT COALESCE(c.name_short_fr, 'N/D') AS sector_name,
               SUM(lm.outstanding_amount)::float AS exposure
        FROM loans l JOIN borrowers b ON b.borrower_id = l.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1 ORDER BY 2 DESC
        """,
        fr)

    def hhi(rows_list):
        total = sum(r["exposure"] for r in rows_list) or 1
        return round(sum((r["exposure"] / total) ** 2 for r in rows_list) * 10_000)

    hhi_sector = hhi(sector_rows)
    hhi_country = hhi(country_rows)
    top10 = query(
        f"""
        SELECT b.display_name, COALESCE(c.name_short_fr, '') AS country,
               SUM(l.outstanding_amount)::float AS exposure
        FROM loans l JOIN borrowers b ON b.borrower_id = l.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        WHERE l.status = 'ACTIVE' {fr_where}
        GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10
        """,
        fr)
    top10_share = sum(r["exposure"] for r in top10) / (exposure or 1) * 100 if top10 else 0

    # ------- observations (dynamically computed from real data) -------
    observations = _observations(fr_where, fr, exposure, top10_share, top10)

    # ------- risk signals (SAP-style thresholds: same as /alerts) -------
    signals = sorted(
        [s for s in top_segments if s["drift"] >= 2.5 or s["npl_ratio"] >= 8],
        key=lambda s: (-s["drift"], -s["npl_ratio"]))[:3]

    return {
        "as_of": as_of,
        "kpis": {
            "exposure": exposure,
            "exposure_delta": round(exposure - prev_exposure, 2) if prev_month else None,
            "npl_ratio": npl_ratio,
            "prev_npl_ratio": prev_npl_ratio,
            "dpd_ratio": delinq / exposure * 100 if exposure else 0,
            "payment_rate": payment_rate,
        },
        "trend": trend,
        "dist": dist,
        "bucket_order": BUCKET_ORDER,
        "bucket_labels": BUCKET_LABELS,
        "segments": top_segments,
        "hhi_sector": hhi_sector,
        "hhi_country": hhi_country,
        "top10": top10,
        "top10_share": top10_share,
        "observations": observations,
        "signals": signals,
        "filters": {"country": country, "sector": sector, "type": btype, "months": months},
        "countries": query("SELECT country_code, name_short_fr FROM countries ORDER BY sort_order"),
        "sectors": query("SELECT DISTINCT sector FROM borrowers WHERE sector IS NOT NULL ORDER BY sector"),
        "types": [("INDIVIDUAL", "Particuliers"), ("SME", "PME"), ("CORPORATE", "Entreprises")],
    }


def _stats_at(month_start, fr_where, fr):
    """Exposure + NPL measured with the information available at a past month."""
    if not month_start:
        return None, 0.0
    r = query(
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF')
                              THEN lm.outstanding_amount END), 0)::float AS exposure,
            COALESCE(SUM(CASE WHEN l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF')
                              AND lm.dpd >= 90 THEN lm.outstanding_amount END), 0)::float AS npl
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND date_trunc('month', lm.as_of_date) = date_trunc('month', %(m)s)
        WHERE l.status IS NOT NULL {fr_where.replace('b.', 'b.')}
        """,
        {**fr, "m": month_start}, one=True)
    return r["exposure"], r["npl"] if r else 0.0


def _observations(fr_where, fr, exposure, top10_share, top10):
    """Short analytics sentences computed from real data only (no fabrication)."""
    obs = []
    exp = exposure or 1
    if top10 and top10_share:
        names = ", ".join(r["display_name"] for r in top10[:3])[:80]
        obs.append(f"Les 10 premières expositions concentrent {top10_share:.1f} % de l'encours (dont {names}…).")
    rm = query(
        f"""
        SELECT b.borrower_type, SUM(lm.outstanding_amount)::float AS exposure
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1
        """,
        fr) if not fr_where else []
    for r in rm:
        if r["exposure"] / exp >= 0.02:
            kind = {"INDIVIDUAL": "particuliers", "SME": "PME", "CORPORATE": "entreprises"}[r["borrower_type"]]
            obs.append(f"Les emprunteurs de type « {kind} » représentent {r['exposure'] / exp * 100:.1f} % de l'exposition totale.")
    segs = query(
        f"""
        SELECT COALESCE(c.name_short_fr, 'N/D') AS country, b.sector,
               SUM(CASE WHEN lm.dpd >= 90 THEN lm.outstanding_amount ELSE 0 END)::float AS npl
        FROM loans l
        JOIN borrowers b ON b.borrower_id = l.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        JOIN loan_monthly lm ON lm.loan_id = l.loan_id
            AND lm.as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)
        WHERE l.status IN ('ACTIVE', 'DEFAULTED', 'WRITTEN_OFF') {fr_where}
        GROUP BY 1, 2 ORDER BY npl DESC LIMIT 1
        """,
        fr)
    if segs and segs[0]["npl"] / exp >= 0.005:
        sg = segs[0]
        obs.append(f"L'encours non performant est concentr\u00e9 sur {sg['country']} \u00b7 {sg['sector']} "
                   f"({sg['npl'] / exp * 100:.1f} % de l'exposition totale).")
    return obs
