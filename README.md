# CreditRisk360 — CEMAC Credit Intelligence & Risk Analytics Platform

![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PosgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-ready-3ECF8E?logo=supabase&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-7%20passed-16a34a)

Plateforme web d'analyse du risque de crédit et d'intelligence de portefeuille
pour la zone **CEMAC** (Cameroun, Centrafrique, Congo, Gabon, Guinée
équatoriale, Tchad) — projet portfolio **Business Analyst / Data Analyst**
dans un contexte inspiré de Creditinfo Central Africa.

> ⚠️ **Données 100 % synthétiques** — projet indépendant et fictif. Aucun
> emprunteur réel ni statistique officiale. Date de référence unique :
> `2026-08-31` (aucune donnée au-delà).

## 🚀 Démarrage rapide

```bash
git clone https://github.com/aliyouck2018/CreditRisk360.git && cd CreditRisk360
make setup            # venv + dépendances + schéma + données synthétiques
python run.py         # → http://localhost:5000
```

Base de données : tout PostgreSQL 14+ (local ou **Supabase**) via la variable
`DATABASE_URL` du fichier `.env`.

---

## 1. Aperçu du produit

CreditRisk360 transforme des données de crédit synthétiques en décisions :
**DONNÉES → KPI → SCORING → ALERTE → ACTION**.

L'application aide un analyste crédit à répondre à des questions telles que :

- Quelle est l'exposition du portefeuille ? Où est le NPL ? Il évolue comment ?
- Quels emprunteurs sont sains, sous surveillance, ou en défaut — et pourquoi ?
- Quels segments (pays × secteur × taille) se dégradent en ce moment ?
- Où sont les concentrations qui violent les limites réglementaires (25 % / 2 %) ?
- Que se passe-t-il si le taux de défaut augmente de 30 % ou les taux de +3 pts ?
- La qualité des données qui alimentent tout cela est-elle fiable ?

### Démarche analytique (démo)

L'application raconte une histoire : *un segment clé se dégrade et les
indicateurs de dette le confirment.*

```
Tableau de bord (NPL en dérive)
  → Risk Analytics (vintage, DPD, concentration HHI)
    → Alertes SAP (segment dégradé + facteurs explicatifs)
      → Fiche Emprunteur 360° (score explicable, historique 36 mois)
        → Stress-Test (chocs défauts / taux / secteur)
          → Analyste IA (destruction analytique en langage naturel)
            → Rapport de crédit PDF (ReportLab A4)
```

## 2. Captures d'écran

### Tableau de bord exécutif
![Tableau de bord](docs/img/dashboard.png)

### Emprunteurs (liste + profils de démonstration)
![Emprunteurs](docs/img/borrowers.png)

### Fiche Emprunteur 360° (score explicable + historique 36 mois)
![Fiche emprunteur](docs/img/borrower_detail.png)

### Risk Analytics (DPD, vintage, heatmap, HHI)
![Risk Analytics](docs/img/risk.png)

### Qualité des données (10 règles + workflow de résolution)
![Qualité des données](docs/img/data_quality.png)

### Alertes SAP (détection précoce avec facteurs « Pourquoi ? »)
![Alertes](docs/img/alerts.png)

### Scorecard explicable
![Scoring](docs/img/scoring.png)

### Simulateur de Stress-Test
![Stress-Test](docs/img/simulator.png)

### Analyste IA en langage naturel (NL2SQL sécurisé)
![Analyste IA](docs/img/analyst.png)

## 3. Fonctionnalités

- **Tableau de bord exécutif** — 6 KPI (encours, emprunteurs, prêts actifs,
  ratio NPL, taux de défaut 12 m, taux de paiement), évolution encours/NPL sur
  24 mois, répartitions pays / secteurs / bandes de risque (ApexCharts).
- **Fiche Emprunteur 360°** — recherche + filtres (pays, secteur, bande de
  risque), pagination, score 300-850 décomposé en points vs profil moyen,
  bandeau interactif de 36 mois d'historique (DPD coloré), facilités,
  consultations bureau, raccourcis vers 5 profils de démo.
- **Risk Analytics** — tranches DPD, analyse vintage par cohorte trimestrielle
  (courbes MOB + heatmap de défaut cumulé), indice HHI, suivi des limites
  réglementaires (secteur ≤ 25 % du pays, emprunteur unique ≤ 2 %) avec
  statuts OK / VIGILANCE / DÉPASSEMENT.
- **Qualité des données** — 10 règles automatisées (DQ-01…DQ-10), score global
  sur 4 dimensions (Complétude, Validité, Unicité, Cohérence), workflow
  *Détecté → En investigation → Corrigé* avec corrections automatiques et
  bouton « Relancer la validation » (recalcul en direct).
- **Alertes (SAP)** — détection des dérives par segment, niveaux
  HIGH / MEDIUM, panneau « Pourquoi ? » attribuant en % la dégradation
  (nouveaux prêts < 6 mois, prêts restructurés, détérioration structurelle).
- **Scoring explicable (W1)** — formule canonique
  `Score = 300 + 550 × Σ(Poidsᵢ × Sous-scoreᵢ)` : paiement 35 %, dette 20 %,
  défauts 15 %, ancienneté 10 %, nouveaux crédits 10 %, demandes 10 %.
- **Stress-Test (W2)** — chocs paramétrables (défaut général 0–100 %, hausse
  des taux 0–5 pts, choc sectoriel ciblé) → NPL et Perte Attendue Base vs
  Stress recalculés en direct (API JSON + graphique).
- **Analyste IA (W3)** — questions en français → SQL en lecture seule :
  `SELECT` uniquement, vues `v_*` uniquement, `LIMIT 500` imposé, catalogues
  système interdits, explication ≤ 120 mots en français.
- **Rapports PDF** — fiche de crédit A4 professionnelle (ReportLab +
  Matplotlib), mention « DONNÉES SYNTHÉTIQUES ».

## 4. Architecture

```
CreditRisk360/
├── app/
│   ├── __init__.py            # app factory + filtres Jinja + blueprint registry
│   ├── metrics.py             # définitions canoniques des KPI (source de vérité)
│   ├── routes/                # 9 blueprints (pages + API /api)
│   ├── services/              # scoring · DQ · NL2SQL · rapport PDF
│   ├── templates/             # Jinja2 (AuditOS design system)
│   └── static/
├── config.py                  # AS_OF_DATE, limites réglementaires, DSN
├── schema.sql                 # 8 tables + 4 vues métier (Supabase-compatible)
├── seed_supabase.py           # générateur déterministe (SEED=42) + scénarios
├── tests/                     # pytest (métier + ngarde-fous IA + workflow DQ)
├── docs/img/                  # captures d'écran
├── run.py · Makefile · requirements.txt · .env (non committé)
```

Vues métier : `v_loans_enriched` (prêts enrichis), `v_kpi_monthly` (KPI
mensuels), `v_segment_monthly` (Pays × Secteur × Taille), `v_borrower_metrics`
(entrée du moteur de score).

## 5. Stack technique

| Couche | Choix |
|---|---|
| Backend | Python 3.11+, Flask 3 (App Factory, Blueprints), Jinja2 |
| Base de données | PostgreSQL (Supabase), accès `psycopg2`, aggégations SQL |
| Frontend | HTML5, Tailwind CSS, Alpine.js, ApexCharts, Lucide — sans framework |
| Rapports | ReportLab + Matplotlib (A4, français) |
| Tests | pytest |
| Divers | python-dotenv · psycopg2 · gunicorn-compatible |

## 6. Définitions canoniques des indicateurs

| Indicateur | Définition stricte |
|---|---|
| **Exposition** | Encours restant dû (`loans.outstanding_amount`), jamais le capital initial |
| **Ratio NPL** | Encours des prêts avec DPD ≥ 90 j / encours total actif |
| **Taux de défaut 12 m** | Prêts franchissant 90 j de retard sur les 12 derniers mois / actifs 12 mois plus tôt |
| **Taux de paiement** | Σ montants payés / Σ montants échus à la date de référence |
| **Dossier vierge** | 0 retard sur 24 mois, aucun impayé, aucun défaut, aucune restructuration |
| **Concentration (HHI)** | `Σ sᵢ² × 10 000` ; limites : secteur ≤ 25 % du pays, emprunteur ≤ 2 % |

Toutes les formules sont implémentées dans [`app/metrics.py`](app/metrics.py)
(documentée également dentro de la page **Méthodologie** de l'application).

## 7. Installation détaillée

Le `make setup` du démarrage rapid enchaîne les étapes ci-dessous —
commandes granulaires :

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
psql "$DATABASE_URL" -f schema.sql               # tables + vues
python seed_supabase.py --dsn "$DATABASE_URL"    # données synthétiques SEED=42
```

`.env` attendu :

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql://...            # Supabase pooler ou Postgres local
```

## 8. Déploiement Supabase

Le schéma est 100 % compatible Supabase (aucun code spécifique) :

```bash
DATABASE_URL='postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres'
psql "$DATABASE_URL" -f schema.sql
python seed_supabase.py --dsn "$DATABASE_URL"
```

Le pooler PgBouncer de Supabase supporte le `COPY ... FROM STDIN` utilisé par
le seed (~800 k lignes en ~1 min).

## 9. Génération de données

```bash
python seed_supabase.py --dsn "$DATABASE_URL"
```

- 6 pays CEMAC · 12 institutions (banques + IMF) · **12 000 emprunteurs**
  (70 % particuliers, 25 % PME, 5 % entreprises) · **20 000 prêts** ·
  ~379 000 échéances de paiement · 378 255 faits mensuels (`loan_monthly`) ·
  consultations bureautiques.
- Corrélations réalistes : montant selon la taille, taux 6,5–14,5 %,
  amortisseur mensuel, dérive comportementale par cohorte.
- **Scénarios métier** injectés :
  - **S1** — dérive des retards sur les prêts récents BTP Cameroun ;
  - **S2** — dépassement des limites : emprunteur unique > 2 %, secteur
    Mines & Pétrole Tchad > 25 % ;
  - **S3** — cohortes 2025 dégradées (défaut ~2× les cohortes 2023-2024) ;
  - **10 anomalies de qualité** plantées pour alimenter le module DQ.
- Reproductible : `SEED=42` ⇒ données identiques.

## 10. Garde-fous Analyste IA

```text
SELECT * FROM v_kpi_monthly            → ✅
SELECT * FROM pg_tables                → ❌ catalogue système
DROP TABLE x                           → ❌ non-SELECT
UPDATE loans SET ...                   → ❌ non sélectionnée
SELECT * FROM countries                → ❌ hors vues v_*
```

`LIMIT 500` imposé automatiquement ; explication générée côté serveur en
≤ 120 mots en citant exclusivement les chiffres retournés.

## 11. Tests

```bash
make test
```

7 tests : cohérence des KPI canoniques (NPL recalculé indépendamment), absence
de données postérieures à la date de référence, garde-fous de l'Analyste IA
(SELECT-only, vues `v_*`, LIMIT 500), workflow de résolution DQ et
correction automatique, conformité des pages (toutes les routes en 200).

## 12. Limites connues

- L'authentification est volontairement absente (MVP portfolio) ; l'utilisateur
  affiché (« Jean Dupont, Manager ») est statique.
- Le scoring calcule une bande de risque par formule déterministe (pas de
  modèle ML entraîné) — l'objectif est l'expliabilité, pas la précision.
- L'Analyste IA utilise un traducteur heuristique déterministe (français →
  SQL) ; un LLM distant (OpenAI/Anthropic) peut le remplacer via la clé API.
