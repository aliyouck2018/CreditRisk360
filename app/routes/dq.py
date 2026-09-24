from flask import Blueprint, abort, jsonify, render_template, request, url_for
from app.services import dq as dq_engine
from app.services.dq import run_all, rule_records, issues_state, set_status

from app.services import dq as dq_engine

dq_eng = dq_engine
dq_bp = Blueprint("dq", __name__)


@dq_bp.route("/")
def index():
    rules, dims, gscore = dq_eng.run_all()
    return render_template(
        "dq/index.html",
        rules=rules,
        dims=dims,
        gscore=gscore,
        fixable=dq_eng.FIXABLE,
    )


@dq_bp.route("/rule/<rule_id>", endpoint="rule_detail")
def rule_detail(rule_id):
    if rule_id not in dq_eng.RULE_BY_ID:
        abort(404)
    records, rule = dq_eng.rule_records(rule_id)
    state = dq_eng.issues_state()
    fields_keys = []
    rows = []
    for r in records:
        if not fields_keys:
            fields_keys = list(r.keys())
        record_id = _record_id(rule_id, r)
        if not record_id:
            continue
        rows.append({"record_id": record_id, "fields": r,
                     "status": state.get(dq_engine.issue_id(rule_id, record_id), "DETECTED")})
    return render_template(
        "dq/records.html",
        rule=rule,
        rows=rows,
        columns=fields_keys,
        fixable=dq_eng.FIXABLE,
    )


def _record_id(rule_id, row):
    if rule_id == "DQ-02":
        return row.get("display_name")
    for k in ("loan_id", "borrower_id", "payment_id"):
        if k in row:
            return row[k]
    return None


@dq_bp.route("/rule/<rule_id>/status", methods=["POST"], endpoint="rule_status")
def rule_status(rule_id):
    record_id = request.form.get("record_id")
    status = request.form.get("status")
    if status not in ("DETECTED", "INVESTIGATING", "RESOLVED"):
        status = "DETECTED"
    set_status(dq_engine.issue_id(rule_id, record_id), rule_id, record_id, status)
    return jsonify({"ok": True, "issue_id": dq_engine.issue_id(rule_id, record_id), "status": status})


@dq_bp.route("/rule/<rule_id>/fix", methods=["POST"], endpoint="rule_fix")
def rule_fix(rule_id):
    record_id = request.form.get("record_id")
    try:
        dq_eng.apply_fix(rule_id, record_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    set_status(dq_engine.issue_id(rule_id, record_id), rule_id, record_id, "RESOLVED")
    return jsonify({"ok": True})


@dq_bp.route("/revalidate", methods=["POST"], endpoint="revalidate")
def revalidate():
    rules, dims, gscore = dq_eng.run_all()
    return jsonify({
        "ok": True,
        "global_score": gscore,
        "dimensions": dims,
        "counts": {r["id"]: {"count": r["count"], "score": r["score"]} for r in rules},
    })


