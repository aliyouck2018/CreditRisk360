from flask import Blueprint, render_template, request

from app.services.db import query
from app.services.scoring import WEIGHTS, score_borrower_row, portfolio_averages, BANDS

scoring_bp = Blueprint("scoring", __name__)

POOL_SQL = """
    SELECT DISTINCT ON (b.borrower_id) b.borrower_id, b.display_name, b.borrower_type,
           COALESCE(c.name_short_fr, 'Inconnu') AS country_name, COALESCE(m.max_dpd, 0) AS max_dpd
    FROM borrowers b
    JOIN loans l ON l.borrower_id = b.borrower_id AND l.status = 'ACTIVE'
    LEFT JOIN countries c ON c.country_code = b.country
    LEFT JOIN v_borrower_metrics m ON m.borrower_id = b.borrower_id
    ORDER BY b.borrower_id, l.outstanding_amount DESC
    LIMIT 30
"""


@scoring_bp.route("/")
def index():
    bid = request.args.get("borrower")
    pool = query(POOL_SQL)
    if not bid and pool:
        bid = pool[0]["borrower_id"]

    row = query(
        """
        SELECT b.*, m.*, COALESCE(c.name_short_fr, 'Inconnu') AS country_name
        FROM borrowers b
        LEFT JOIN v_borrower_metrics m ON m.borrower_id = b.borrower_id
        LEFT JOIN countries c ON c.country_code = b.country
        WHERE b.borrower_id = %(bid)s
        """,
        {"bid": bid}, one=True)
    scored = score_borrower_row(row) if row else None

    return render_template(
        "scoring/index.html",
        pool=pool,
        selected_row=row,
        scored=scored,
        weights=WEIGHTS,
        portfolio_avg=portfolio_averages(),
        bands=BANDS,
    )
