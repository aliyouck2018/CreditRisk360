from flask import Blueprint, render_template

from app.services.db import query

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
def dashboard():
    from app.services.dashboard import get_dashboard_context
    return render_template("dashboard.html", **get_dashboard_context())


@main_bp.route("/reports")
def reports():
    demos = query(
        """
        SELECT b.borrower_id, b.display_name, b.borrower_type, c.name_short_fr AS country_name
        FROM borrowers b LEFT JOIN countries c ON c.country_code = b.country
        WHERE b.is_demo OR b.borrower_id ILIKE 'BRW-DEMO%%'
        ORDER BY b.borrower_id
        """)
    return render_template("reports.html", demos=demos)


@main_bp.route("/methodology")
def methodology():
    return render_template("methodology.html")