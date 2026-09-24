from flask import Blueprint, render_template

from app import metrics

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
def dashboard():
    kpi = metrics.kpi_summary()
    trend = metrics.monthly_trend()
    bands = metrics.risk_band_distribution()
    countries = metrics.exposure_by_country()
    sectors = metrics.exposure_by_sector()
    import json
    ctx = {
        "kpi": kpi,
        "trend": trend,
        "bands": bands,
        "trend_labels_json": json.dumps(trend["labels"]),
        "trend_exposure_json": json.dumps(trend["exposure"]),
        "trend_npl_json": json.dumps(trend["npl"]),
        "bands_names_json": json.dumps([b["name"] for b in bands]),
        "bands_values_json": json.dumps([b["value"] for b in bands]),
        "country_names_json": json.dumps([c["name"] for c in countries]),
        "country_values_json": json.dumps([round(c["value"] / 1e9, 1) for c in countries]),
        "sector_names_json": json.dumps([s["name"] for s in sectors]),
        "sector_values_json": json.dumps([round(s["value"] / 1e9, 1) for s in sectors]),
    }
    return render_template("dashboard.html", **ctx)


@main_bp.route("/methodology")
def methodology():
    return render_template("methodology.html")