import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central application configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Database: local Postgres by default, Supabase-compatible via DATABASE_URL
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/creditrisk360",
    )

    # Reference date: all data is as of this date, nothing after
    AS_OF_DATE = date(2026, 8, 31)

    # CEMAC scope
    CEMAC_COUNTRIES = ["CMR", "CAF", "COG", "GAB", "GNQ", "TCD"]

    # Risk Analytics regulatory limits
    SECTOR_CONCENTRATION_LIMIT = 25.0  # % of portfolio
    SINGLE_BORROWER_LIMIT = 2.0  # % of portfolio

    # AI Analyst guardrails
    SQL_MAX_ROWS = 500

    # Demo borrower profiles for quick access
    DEMO_BORROWER_IDS = []
