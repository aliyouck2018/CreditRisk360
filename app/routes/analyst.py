from flask import Blueprint, jsonify, render_template, request

from app.services import ai_analyst

analyst_bp = Blueprint("analyst", __name__)


@analyst_bp.route("/")
def index():
    return render_template("analyst/index.html")


@analyst_bp.route("/query", methods=["POST"], endpoint="query")
def query_endpoint():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Question vide."}), 400
    result = ai_analyst.answer(question)
    return jsonify(result)
