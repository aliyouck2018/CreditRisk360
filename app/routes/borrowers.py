from datetime import date

from flask import Blueprint, abort, render_template, request

from app import metrics
from app.services.db import query
from app.services.scoring import score_borrower_row

borrowers_bp = Blueprint("borrowers", __name__)

PAGE_SIZE = 20

DEMO_PROFILE_META = {
    "BRW-DEMO-01": ("Sain", "badge-green-fg", "bg-badge-green-bg"),
    "BRW-DEMO-02": ("Sous surveillance", "badge-amber-fg", "bg-badge-amber-bg"),
    "BRW-DEMO-03": ("En défaut", "badge-red-fg", "bg-badge-red-bg"),
    "BRW-DEMO-04": ("Multi-institutions", "badge-blue-fg", "bg-badge-blue-bg"),
    "BRW-DEMO-05": ("Nouveau", "badge-blue-fg", "bg-badge-blue-bg"),
}


def _filters():
    q = request.args.get("q", "").strip()
    country = request.args.get("country", "")
    sector = request.args.get("sector", "")
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    return q, country, sector, page


@borrowers_bp.route("/", endpoint="borrower_list")
def borrower_list():
    q, country, sector, page = _filters()
    params = {"as_of": metrics.as_of_date()}

    where = ["l.status = 'ACTIVE'"]
    if q:
        where.append("b.display_name ILIKE %(q)s")
        params["q"] = f"%{q}%"
    if country:
        where.append("b.country = %(country)s")
        params["country"] = country
    if sector:
        where.append("b.sector = %(sector)s")
        params["sector"] = sector
    where_sql = " AND ".join(where)

    total = query(
        f"""
        SELECT COUNT(DISTINCT b.borrower_id) AS cnt
        FROM borrowers b JOIN loans l ON l.borrower_id = b.borrower_id
        WHERE {where_sql}
        """,
        params, one=True)["cnt"]

    rows = query(
        f"""
        SELECT DISTINCT ON (b.borrower_id)
               b.borrower_id, b.display_name, b.borrower_type, b.country,
               c.name_short_fr AS country_name, b.sector, b.registration_date, b.is_demo,
               m.total_outstanding, m.max_dpd, m.n_defaults, m.paid_ratio_12m
        FROM borrowers b
        JOIN loans l ON l.borrower_id = b.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        LEFT JOIN v_borrower_metrics m ON m.borrower_id = b.borrower_id
        WHERE {where_sql}
        ORDER BY b.borrower_id, m.total_outstanding DESC
        LIMIT {PAGE_SIZE + 1} OFFSET %(offset)s
        """,
        {**params, "offset": (page - 1) * PAGE_SIZE},
    )

    items = []
    for r in rows[:PAGE_SIZE]:
        s = score_borrower_row(r)
        items.append({**r, **s})
    has_next = len(rows) > PAGE_SIZE

    demo = query(
        "SELECT borrower_id, display_name, country FROM borrowers WHERE is_demo AND borrower_id LIKE '%%DEMO%%' ORDER BY borrower_id")

    return render_template(
        "borrowers/list.html",
        items=items,
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        has_next=has_next,
        has_prev=page > 1,
        q=q,
        country=country,
        sector=sector,
        demo=demo,
        demo_meta=DEMO_PROFILE_META,
        countries=query("SELECT country_code, name_short_fr FROM countries ORDER BY sort_order"),
        sectors=query("SELECT DISTINCT sector FROM borrowers WHERE sector IS NOT NULL ORDER BY sector"),
    )


@borrowers_bp.route("/<borrower_id>", endpoint="borrower_detail")
def borrower_detail(borrower_id):
    b = query(
        """
        SELECT b.*, c.name_short_fr AS country_name, c.name_full_fr AS country_full
        FROM borrowers b LEFT JOIN countries c ON c.country_code = b.country
        WHERE b.borrower_id = %(bid)s
        """,
        {"bid": borrower_id}, one=True)
    if not b:
        abort(404)

    m = metrics.borrower_metrics(borrower_id)
    scored = score_borrower_row(m if m else {
        "borrower_id": borrower_id, "borrower_type": b["borrower_type"],
        "registration_date": b["registration_date"], "total_outstanding": 0,
        "max_dpd": 0, "n_defaults": 0, "restructured_loans": 0,
        "n_recent_loans": 0, "paid_ratio_12m": 1.0, "n_enquiries": 0,
    })

    loans = query(
        """
        SELECT l.*, i.name AS institution_name,
               d.dpd AS current_dpd, d.dpd_bucket
        FROM loans l
        LEFT JOIN institutions i ON i.institution_id = l.institution_id
        LEFT JOIN (SELECT loan_id, dpd, dpd_bucket FROM loan_monthly
                   WHERE as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)) d ON d.loan_id = l.loan_id
        WHERE l.borrower_id = %(bid)s
        ORDER BY l.status, l.outstanding_amount DESC
        """,
        {"bid": borrower_id})

    history = query(
        """
        SELECT to_char(due_date, 'MM/YYYY') AS m,
               SUM(amount_due) AS due, SUM(amount_paid) AS paid,
               MAX(days_past_due) AS max_dpd,
               COUNT(*) FILTER (WHERE payment_date IS NULL AND due_date <= %(as_of)s) AS missed
        FROM payments p JOIN loans l USING (loan_id)
        WHERE l.borrower_id = %(bid)s AND due_date <= %(as_of)s
        GROUP BY 1
        ORDER BY MIN(due_date)
        """,
        {"bid": borrower_id, "as_of": metrics.as_of_date()})

    enquiries = query(
        """
        SELECT e.enquiry_date, e.purpose, i.name AS institution_name
        FROM enquiries e JOIN institutions i USING (institution_id)
        WHERE e.borrower_id = %(bid)s
        ORDER BY e.enquiry_date DESC LIMIT 10
        """,
        {"bid": borrower_id})

    # legal form guess from display name
    name = b["display_name"]
    legal_form = next((f for f in ("SARL", "SA", "ETS", "Groupe") if f in name), "—")

    return render_template(
        "borrowers/detail.html",
        borrower=b,
        metrics=m or {},
        score=scored,
        loans=loans,
        history=history[-36:],
        enquiries=enquiries,
        legal_form=legal_form,
        demo_meta=DEMO_PROFILE_META,
    )


@borrowers_bp.route("/<borrower_id>/pdf", endpoint="borrower_pdf")
def borrower_pdf(borrower_id):
    from flask import Response
    from app.services.pdf_report import generate_credit_report
    pdf = generate_credit_report(borrower_id)
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f"inline; filename=rapport_credit_{borrower_id}.pdf"})
