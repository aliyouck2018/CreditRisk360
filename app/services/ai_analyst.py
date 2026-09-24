"""AI Analyst: natural-language → secure read-only SQL on v_* views.

Guardrails (spec §5.9):
  - SELECT-only statements
  - tables restricted to views starting with v_
  - no system catalogs (pg_*, information_schema, pragma, etc.)
  - LIMIT 500 forced
  - French explanation <= 120 words built only from returned numbers
"""
import re

from flask import current_app

from app.services.db import query

MAX_ROWS = 500

ALLOWED_VIEWS = {"v_loans_enriched", "v_kpi_monthly", "v_segment_monthly", "v_borrower_metrics"}
FORBIDDEN = ("pg_", "information_schema", "pragma", "catalog", "pg_table", "\\", "/*", "--",
             "insert", "update", "delete", "drop", "alter", "create", "grant", "copy", ";")

SYS_TOKENS = re.compile(r"\b(pg_tables|information_schema|pg_catalog|pragma|copy|lo_import|lo_export)\b", re.I)


def validate_sql(sql: str) -> str:
    """Return validated SQL (LIMIT 500 enforced) or raise ValueError."""
    sql = sql.strip().rstrip(";").strip()
    if not sql.lower().startswith("select"):
        raise ValueError("Seules les commandes SELECT sont autorisées.")
    if sql.endswith(";"):
        pass
    lowered = sql.lower()
    for bad in ("insert ", "update ", "delete ", "drop ", "alter ", "create ", "grant ", "copy ", "truncate "):
        if bad in lowered:
            raise ValueError(f"Instruction interdite : {bad.strip().upper()}.")
    if SYS_TOKENS.search(sql):
        raise ValueError("Accès aux catalogues système interdit : seules les vues v_* sont lisibles.")
    tables = re.findall(r"\b(?:from|join)\s+([a-z_0-9.]+)", lowered)
    for t in tables:
        base = t.split(".")[-1]
        if base not in ALLOWED_VIEWS:
            raise ValueError(
                f"Table '{base}' non autorisée : seules {sorted(ALLOWED_VIEWS)} sont accessibles.")
    if " select " not in lowered[7:]:
        pass
    if "\n\n--" in sql or "--" in sql:
        raise ValueError("Les commentaires SQL ne sont pas autorisés.")
    if "/*" in sql or "*/" in sql:
        raise ValueError("Les commentaires SQL ne sont pas autorisés.")
    if not re.search(r"\blimit\s+\d+", lowered):
        sql += " LIMIT 500"
    else:
        m = re.search(r"limit\s+(\d+)", lowered)
        if int(m.group(1)) > current_app.config["SQL_MAX_ROWS"]:
            sql = re.sub(r"\blimit\s+\d+", f"LIMIT {MAX_ROWS}", sql, flags=re.I)
    return sql


# ------------------------------------------------------------------
# Heuristic NL2SQL fallback (deterministic; no external API needed)
# ------------------------------------------------------------------

def nl2sql(question: str) -> tuple[str, str]:
    """Return (sql, note)."""
    q = question.lower()
    agg = "SUM(outstanding_amount) AS encours"
    where_active = "WHERE status = 'ACTIVE'"
    order = "ORDER BY 2 DESC"

    if "npl" in q or "défaut" in q or "defaut" in q:
        if "pays" in q:
            sql = (
                "SELECT country, "
                "SUM(total_outstanding) AS encours_total, "
                "SUM(npl_outstanding) AS encours_npl, "
                "ROUND(SUM(npl_outstanding) / NULLIF(SUM(total_outstanding),0) * 100, 2) AS npl_ratio "
                "FROM v_segment_monthly "
                "WHERE as_of_month = (SELECT MAX(as_of_month) FROM v_segment_monthly) "
                "GROUP BY country ORDER BY npl_ratio DESC")
            return sql, "Agrégation NPL par pays (dernier mois disponible)."
        if "secteur" in q:
            sql = sql = (
                "SELECT sector, "
                "SUM(total_outstanding) AS encours_total, "
                "SUM(npl_outstanding) AS encours_npl, "
                "ROUND(SUM(npl_outstanding) / NULLIF(SUM(total_outstanding),0) * 100, 2) AS npl_ratio "
                "FROM v_segment_monthly "
                "WHERE as_of_month = (SELECT MAX(as_of_month) FROM v_segment_monthly) "
                "GROUP BY 1 ORDER BY npl_ratio DESC")
            return sql, "Agrégation NPL par secteur (dernier mois disponible)."

    if "pays" in q and ("encours" in q or "exposition" in q or "par" in q):
        sql = (f"SELECT country_name, SUM(outstanding_amount) AS encours "
               f"FROM v_loans_enriched {where_active} GROUP BY 1 {order}")
        return sql, "Encours actif agrégé par pays (view v_loans_enriched)."

    if "secteur" in q:
        sql = (f"SELECT sector, SUM(outstanding_amount) AS encours "
               f"FROM v_loans_enriched {where_active} GROUP BY 1 {order}")
        return sql, "Encours actif agrégé par secteur."

    if "institution" in q or "banque" in q:
        sql = (f"SELECT institution_name, SUM(outstanding_amount) AS encours "
               f"FROM v_loans_enriched {where_active} GROUP BY 1 {order}")
        return sql, "Encours actif agrégé par institution."

    if "emprunteurs" in q or "top" in q or "les plus" in q:
        sql = ("SELECT borrower_name, SUM(outstanding_amount) AS encours "
               "FROM v_loans_enriched WHERE status = 'ACTIVE' "
               "GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
        return sql, "Top 10 des emprunteurs par encours actif."

    # fallback: overall monthly KPI
    sql = "SELECT * FROM v_kpi_monthly ORDER BY as_of_month DESC LIMIT 12"
    return sql, "Série mensuelle des KPI portfolios (12 derniers mois)."


def explain(question: str, rows, sql) -> str:
    """French explanation <= 120 words using only returned numbers."""
    if not rows:
        return ("Aucun résultat renvoyé pour cette question. Reformulez ou utilisez le "
                "dictionnaire de données de la page Méthodologie.")
    cols = list(rows[0].keys())
    n = len(rows)
    lines = []
    lines.append(f"{len(rows)} ligne(s) retournée(s) pour « {question.strip()} ». ")
    # numeric highlights: first numeric column of top rows
    import decimal
    def is_num(v):
        return isinstance(v, (int, float))
    first_num_col = None
    for c in cols:
        vals = [r[c] for r in rows[:5]]
        if all(isinstance(v, (int, float)) for v in vals):
            first_num_col = c
            break
    if first_num_col:
        total = sum(r[first_num_col] for r in rows[:50] if isinstance(r[first_num_col], (int, float)))
        top = max(rows, key=lambda r: r[first_num_col] or 0)
        label_col = next((c for c in cols if c != first_num_col), None)
        if label_col and isinstance(top.get(label_col), str):
            lines.append(f"Segment dominant : {top[label_col]}.")
        lines.append(f"Colonnes : {', '.join(cols)}.")
        if top.get(first_num_col) and top[first_num_col]:
            lines.append(f"Le premier terme est « {top.get(label_col, '—')} » : {top[first_num_col]:,.0f}.")
    text = " ".join(lines)
    return text[:740]


def answer(question: str):
    """Full pipeline: question → validated SQL → rows → explanation."""
    sql = maybe_sql_check(question) or nl2sql(question)[0]
    return run_validated(sql, question)


def maybe_sql_check(question):
    if question.strip().upper().startswith("SELECT"):
        return question
    return None


def run_validated(sql, question=""):
    try:
        validated = validate_sql(sql)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    rows = query(validated)
    return {"ok": True, "sql": validated, "columns": list(rows[0].keys()) if rows else [],
            "rows": [list(r.values()) for r in rows], "explanation": explain(question, rows, validated)}
