"""Explainable scoring engine (canonical formula).

Score = 300 + 550 * SUM(weight_i * subscore_i), subscores in [0, 1].

Weights (sum = 1.0):
  - Payment history      0.35
  - Exposure / capacity  0.20
  - Delinquency flags    0.15
  - Credit history age   0.10
  - New credit demand    0.10
  - Enquiry pressure     0.10
"""
from datetime import date

# ---- canonical weights -------------------------------------------------
WEIGHTS = {
    "pillarity_payment": ("Historique de paiement", 0.35),
    "pillarity_exposure": ("Niveau d'endettement", 0.20),
    "pillarity_flags": ("Antécédents de défaut", 0.15),
    "pillarity_history": ("Ancienneté de relation", 0.10),
    "pillarity_new": ("Nouveaux crédits", 0.10),
    "pillarity_enquiries": ("Pression des demandes", 0.10),
}

# Portfolio-average subscores (computed once from DB at first call)
_portfolio_avg = None

BANDS = [
    (730, "Faible", "badge-green-fg", "bg-badge-green-bg", "#16A34A"),
    (650, "Modéré", "badge-blue-fg", "bg-badge-blue-bg", "#0284C7"),
    (570, "Élevé", "badge-amber-fg", "bg-badge-amber-bg", "#D97706"),
    (-1e9, "Très Élevé", "badge-red-fg", "bg-badge-red-bg", "#DC2626"),
]


def portfolio_averages():
    """Portfolio-average subscores (cached per app process)."""
    global _portfolio_avg
    if _portfolio_avg is None:
        from app.services.db import query
        rows = query(
            """
            SELECT b.borrower_id, b.borrower_type, b.registration_date,
                   COALESCE(m.max_dpd,0) max_dpd, COALESCE(m.total_outstanding,0) t_out,
                   COALESCE(m.n_defaults,0) nd, COALESCE(m.restructured_loans,0) nres,
                   COALESCE(m.n_recent_loans,0) nrec, COALESCE(m.paid_ratio_12m,1) pr,
                   COALESCE(m.n_enquiries,0) nq
            FROM borrowers b LEFT JOIN v_borrower_metrics m USING (borrower_id)
            LIMIT 300
            """,
        )
        subs = [compute_subscores(r["borrower_type"], r["registration_date"],
                                  float(r["max_dpd"]), float(r["t_out"]),
                                  r["nd"], r["nres"], r["nrec"],
                                  float(r["pr"]), r["nq"])
                for r in rows]
        _portfolio_avg = {k: sum(s[k] for s in subs) / len(subs) for k in subs[0]}
    return _portfolio_avg


def compute_subscores(borrower_type, registration_date, max_dpd, total_outstanding,
                      n_defaults, n_restructured, n_recent, paid_ratio_12m, n_enquiries):
    """Raw subscores from raw metrics (all inputs from v_borrower_metrics)."""
    total_outstanding = max(0.0, float(total_outstanding))
    if registration_date is not None and not hasattr(registration_date, "year"):
        registration_date = None
    # 1. Payment history: 12m ratio + recent DPD penalty
    dpd_pen = min(1.0, max_dpd / 90.0) * 0.8
    s_payment = max(0.0, (paid_ratio_12m ** 1.5) - dpd_pen)

    # 2. Debt level: outstanding vs type-based capacity
    cap = {"INDIVIDUAL": 8e6, "SME": 60e6, "CORPORATE": 400e6}[borrower_type]
    s_debt = max(0.0, 1.0 - (total_outstanding / cap) ** 0.6 / 1.2)

    # 3. Delinquency flags
    s_flags = max(0.0, 1.0 - 0.62 * n_defaults - 0.15 * n_restructured)

    # 4. History age (years since registration, capped at 8y)
    age_y = (date(2026, 8, 31) - registration_date).days / 365.25 if registration_date else 0
    s_history = max(0.0, min(1.0, age_y / 8.0))

    # 5. New credit demand (<6m)
    s_new = max(0.0, 1.0 - 0.7 * min(n_recent, 2) / 2.0)

    # 6. Enquiry pressure (12m)
    s_enq = max(0.0, 1.0 - min(n_enquiries, 6) / 6.0)

    return {
        "pillarity_payment": s_payment,
        "pillarity_exposure": s_debt,
        "pillarity_flags": s_flags,
        "pillarity_history": s_history,
        "pillarity_new": s_new,
        "pillarity_enquiries": s_enq,
    }


def score_borrower_row(row):
    """Score a v_borrower_metrics-joined row dict."""
    r = row
    subs = compute_subscores(
        r.get("borrower_type") or "INDIVIDUAL",
        r.get("registration_date") or date(2024, 1, 1),
        float(r.get("max_dpd") or 0),
        float(r.get("total_outstanding") or 0),
        r.get("n_defaults") or 0,
        r.get("restructured_loans") or 0,
        r.get("n_recent_loans") or 0,
        float(r.get("paid_ratio_12m") if r.get("paid_ratio_12m") is not None else 1.0),
        r.get("n_enquiries") or 0,
    )
    return explain(subs)


def explain(subs):
    """Compute final score from subscores + contribution point breakdown."""
    weighted = sum(WEIGHTS[k][1] * subs[k] for k in WEIGHTS)
    score = round(300 + 550 * weighted)
    contributions = []
    for k, (label, w) in WEIGHTS.items():
        pts = round(550 * w * subs[k])
        avg = round(550 * w * portfolio_averages()[k])
        contributions.append({
            "key": k,
            "label": label,
            "subscore": round(subs[k], 2),
            "points": pts,
            "portfolio_avg_points": avg,
            "delta": pts - avg,
        })
    contributions.sort(key=lambda c: -c["delta"])
    band = "Très Élevé"
    for threshold, name, *_ in BANDS:
        if score >= threshold:
            band = name
            break
    return {
        "score": score,
        "weighted": weighted,
        "risk_band": band,
        "contributions": contributions,
    }
