"""Professional credit report PDF generator (ReportLab, A4, French).

Reports carry the mandatory synthetic-data disclaimer.
"""
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from app import metrics
from app.services.db import query
from app.services.scoring import score_borrower_row

AUDIT_DARK = colors.HexColor("#111827")
AUDIT_PURPLE = colors.HexColor("#5B50E5")
LIGHT_GRAY = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")

SYNTHETIC_NOTICE = "DONNÉES SYNTHÉTIQUES — RAPPORT DE DÉMONSTRATION"


def _payment_chart(borrower_id, history) -> io.BytesIO | None:
    if not history:
        return None
    import matplotlib
    plt = matplotlib.pyplot
    fig, ax = plt.subplots(figsize=(7, 2.2), dpi=110)
    labels = [h["m"] for h in history]
    paid = [float(h["paid"]) / 1e6 for h in history]
    due = [float(h["due"]) / 1e6 for h in history]
    x = range(len(labels))
    ax.bar(x, due, color="#CBD5E1", label="Échus (M XAF)", width=0.65)
    ax.bar(x, paid, color="#5B50E5", label="Payés (M XAF)", width=0.38)
    step = max(1, len(labels) // 12)
    ax.set_xticks(list(x)[::step])
    ax.set_xticklabels([l for l in labels][::step], fontsize=6.5)
    ax.tick_params(labelsize=6.5)
    ax.legend(fontsize=6.5, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_credit_report(borrower_id: str) -> bytes:
    b = query(
        """
        SELECT b.*, c.name_short_fr AS country_name
        FROM borrowers b LEFT JOIN countries c ON c.country_code = b.country
        WHERE b.borrower_id = %(bid)s
        """,
        {"bid": borrower_id}, one=True)
    if not b:
        raise LookupError("unknown borrower")

    m = metrics.borrower_metrics(borrower_id)
    scored = score_borrower_row(m if m else {
        "borrower_id": borrower_id, "borrower_type": b["borrower_type"],
        "registration_date": b["registration_date"], "total_outstanding": 0,
        "max_dpd": 0, "n_defaults": 0, "restructured_loans": 0, "n_recent_loans": 0,
        "paid_ratio_12m": 1.0, "n_enquiries": 0,
    })
    loans = query(
        """
        SELECT l.*, i.name AS institution_name, d.dpd AS current_dpd
        FROM loans l LEFT JOIN institutions i ON i.institution_id = l.institution_id
        LEFT JOIN (SELECT loan_id, dpd FROM loan_monthly
                   WHERE as_of_date = (SELECT MAX(as_of_date) FROM loan_monthly)) d ON d.loan_id = l.loan_id
        WHERE l.borrower_id = %(bid)s ORDER BY l.outstanding_amount DESC
        """,
        {"bid": borrower_id})
    history = query(
        """
        SELECT to_char(due_date, 'MM/YYYY') AS m, SUM(amount_due) AS due,
               SUM(amount_paid) AS paid
        FROM payments p JOIN loans l USING (loan_id)
        WHERE l.borrower_id = %(bid)s AND due_date <= %(as_of)s
        GROUP BY 1 ORDER BY MIN(due_date)
        """,
        {"bid": borrower_id, "as_of": metrics.as_of_date()})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=(210 * mm, 297 * mm),
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=f"Rapport de crédit - {b['display_name']}")
    styles = getSampleStyleSheet()
    h1 = styles["Title"]
    h1.fontSize = 16
    h1.textColor = AUDIT_DARK
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11.5,
                        textColor=AUDIT_PURPLE, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=12.5)

    story = []

    # Header band
    type_label = {"INDIVIDUAL": "Particulier", "SME": "PME", "CORPORATE": "Entreprise"}[b["borrower_type"]]
    title_tbl = Table([
        [Paragraph(f"<font color='#5B50E5'><b>CreditRisk360</b></font> — <font color='white'>Rapport de Crédit</font>",
                   ParagraphStyle("t", fontSize=13, textColor=colors.white, leading=17)),
         Paragraph(SYNTHETIC_NOTICE, ParagraphStyle("n", fontSize=7.5, alignment=2, textColor=colors.HexColor("#FBBF24"), leading=9))],
        [Paragraph(f"<b>{b['display_name']}</b> · {b.get('country_name') or '—'} · "
                   f"{type_label} · "
                   f"ID {b['borrower_id']}", ParagraphStyle("sub", fontSize=9.5, textColor=colors.white, leading=13)),
         Paragraph(f"Données au {metrics.as_of_date().strftime('%d/%m/%Y')} — Creditinfo Central Africa (interface de démonstration)",
                   ParagraphStyle("sub2", fontSize=7.5, alignment=2, textColor=colors.HexColor("#9CA3AF"), leading=9))],
    ], colWidths=[120 * mm, 58 * mm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AUDIT_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [title_tbl, Spacer(1, 8 * mm)]

    # Score box
    story.append(Paragraph("Synthèse de risque explicable", h2))
    score_rows = [["Score (300–850)", "Bande de risque", "Encours total", "Prêts actifs", "DPD max (24 m)", "Taux de paiement 12 m"],
                  [str(scored["score"]), scored["risk_band"],
                   f"{(m or {}).get('total_outstanding', 0):,.0f} XAF".replace(",", " ").replace(".0", ""),
                   str((m or {}).get("n_active_loans", 0)), str((m or {}).get("max_dpd", 0)),
                   f"{((m or {}).get('paid_ratio_12m', 1) * 100):.1f} %"]]
    score_tbl = Table(score_rows, colWidths=[27 * mm, 27 * mm, 37 * mm, 26 * mm, 27 * mm, 34 * mm])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(score_tbl)

    # Factor breakdown
    story.append(Paragraph("Décomposition du score (vs profil moyen du portefeuille)", h2))
    factor_rows = [["Facteur", "Contribution (pts)", "Moyenne portefeuille (pts)", "Écart"]]
    for c in scored["contributions"]:
        factor_rows.append([c["label"], str(c["points"]), str(c["portfolio_avg_points"]),
                            f"{c['delta']:+d}"])
    f_tbl = Table(factor_rows, colWidths=[64 * mm, 38 * mm, 50 * mm, 26 * mm])
    f_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(f_tbl)

    # Facilities
    story.append(Paragraph("Facilités de crédit", h2))
    loan_rows = [["Loan ID", "Institution", "Type", "Capital initial", "Encours", "Échéance", "Statut", "DPD"]]
    for l in loans:
        loan_rows.append([
            l["loan_id"], l["institution_name"], l["loan_type"],
            f"{float(l['principal_amount']):,.0f}", f"{float(l['outstanding_amount']):,.0f}",
            (l["maturity_date"].strftime("%d/%m/%Y") if l["maturity_date"] else "n/d"),
            {"ACTIVE": "Encours", "CLOSED": "Soldé", "DEFAULTED": "Défaut", "WRITTEN_OFF": "Annulé"}[l["status"]],
            f"{l.get('current_dpd') or 0} j"])
    loan_tbl = Table(loan_rows, colWidths=[20 * mm, 34 * mm, 26 * mm, 24 * mm, 24 * mm, 22 * mm, 18 * mm, 14 * mm])
    loan_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (3, 1), (5, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(loan_tbl)

    # Payment history chart
    story.append(Paragraph("Historique de paiement", h2))
    chart = _payment_chart(borrower_id, history[-24:])
    if chart:
        story.append(Image(chart, width=178 * mm, height=178 * 2.2 / 7.0))
    story.append(Paragraph(
        "<i>Ce rapport est généré automatiquement par CreditRisk360 sur données 100% synthétiques. "
        "Aucune information réelle d'emprunteur n'est utilisée. Source : interface Creditinfo Central Africa (démo).</i>",
        ParagraphStyle("foot", parent=body, fontSize=7, textColor=colors.HexColor("#6B7280"))))

    doc.build(story)
    return buf.getvalue()
