"""Application factory for CreditRisk360."""
import os

from flask import Flask

from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure DATABASE_URL uses psycopg2 driver
    db_url = app.config.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        app.config["DATABASE_URL"] = db_url.replace("postgres://", "postgresql://", 1)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.borrowers import borrowers_bp
    from app.routes.risk import risk_bp
    from app.routes.dq import dq_bp
    from app.routes.alerts import alerts_bp
    from app.routes.scoring import scoring_bp
    from app.routes.simulator import simulator_bp
    from app.routes.analyst import analyst_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(borrowers_bp, url_prefix="/borrowers")
    app.register_blueprint(risk_bp, url_prefix="/risk")
    app.register_blueprint(dq_bp, url_prefix="/data-quality")
    app.register_blueprint(alerts_bp, url_prefix="/alerts")
    app.register_blueprint(scoring_bp, url_prefix="/scoring")
    app.register_blueprint(simulator_bp, url_prefix="/simulator")
    app.register_blueprint(analyst_bp, url_prefix="/analyst")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Jinja globals
    from app.services.db import get_db

    @app.template_filter("xaf")
    def format_xaf(value):
        """Format a number as billions of XAF."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "—"
        if abs(v) >= 1_000_000_000:
            return f"{v / 1_000_000_000:,.1f} Md XAF".replace(",", " ")
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:,.1f} M XAF".replace(",", " ")
        return f"{v:,.0f} XAF".replace(",", " ")

    @app.template_filter("num")
    def format_num(value):
        try:
            return f"{float(value):,.0f}".replace(",", " ")
        except (TypeError, ValueError):
            return "—"

    @app.context_processor
    def inject_globals():
        return {
            "AS_OF_DATE": app.config["AS_OF_DATE"],
            "app_name": "CreditRisk360",
        }

    @app.teardown_appcontext
    def close_db(exception):
        get_db().close()

    return app