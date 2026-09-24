from flask import Blueprint, jsonify, request

from app.routes.simulator import base_state, LGD

api_bp = Blueprint("api", __name__)


@api_bp.route("/simulator/stress", methods=["POST"])
def stress_compute():
    """Recompute stressed portfolio metrics from shock parameters."""
    data = request.get_json(silent=True) or {}
    try:
        default_shock = float(data.get("default_shock", 0)) / 100.0  # 0..1
        rate_shock = float(data.get("rate_shock", 0))                # points
        sector_shock = float(data.get("sector_shock", 0)) / 100.0    # 0..1
        target_sector = data.get("target_sector", "")
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Paramètres invalides"}), 400

    s = base_state()
    exposure = s["exposure"]
    npl = s["npl"]
    performing = exposure - npl
    pd_perf = s["pd_performing"]

    sector_perf = 0.0
    for row in s["sectors"]:
        if row["sector"] == target_sector:
            sector_perf = float(row["exposure"]) * (performing / exposure if exposure else 0)
            break

    # Stress: fraction of performing exposure migrating into the 90+ bucket
    migrated = (default_shock * performing
                + sector_shock * sector_perf
                + rate_shock * 0.012 * performing)
    npl_stressed = npl + migrated
    npl_ratio_base = npl / exposure * 100 if exposure else 0
    npl_ratio_st = npl_stressed / exposure * 100 if exposure else 0

    # Expected Loss: defaulted exposure × LGD + performing × PD × LGD
    el_base = (npl * LGD) + (performing * pd_perf) * LGD
    performing_st = max(0.0, performing - migrated)
    el_stressed = (npl_stressed * LGD) + (performing_st * pd_perf) * LGD

    return jsonify({
        "ok": True,
        "base": {
            "npl_ratio": round(npl_ratio_base, 2),
            "el": round(el_base),
        },
        "stress": {
            "npl_ratio": round(npl_ratio_st, 2),
            "el": round(el_stressed),
        },
    })