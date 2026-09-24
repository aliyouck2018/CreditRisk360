# CAHIER DES CHARGES TECHNIQUE ET FONCTIONNEL V2.0
## CreditRisk360 — CEMAC Credit Intelligence & Risk Analytics Platform

- **Statut :** Document de référence pour l'agent de développement (GLM 5.3 Flash)
- **Stack :** Python (Flask) + Supabase (PostgreSQL) + Jinja2 + Tailwind CSS + Alpine.js + ApexCharts
- **Design System :** Inspiring Mockup AuditOS (Sidebar sombre `#111827`, accent violet `#5B50E5`, cartes KPI épurées, badges pastel)
- **Date de référence des données :** 31 août 2026 (`AS_OF_DATE = 2026-08-31`)
- **Périmètre géographique :** Zone CEMAC (CMR, CAF, COG, GAB, GNQ, TCD)

---

## 1. VISION, OBJECTIFS ET CONTEXTE

### 1.1 Objet du projet
**CreditRisk360** est une plateforme web full-stack d'analyse du risque de crédit et d'intelligence de portefeuille pour la zone CEMAC. Développée dans le cadre d'un portfolio pour un poste de **Business Analyst / Data Analyst** chez Creditinfo Central Africa, l'application utilise **100 % de données synthétiques** et simule un environnement décisionnel complet :
- Tableau de bord exécutif de portefeuille (exposition, NPL, scoring).
- Vue Emprunteur 360° avec score explicable et historique de paiement.
- Analyses avancées du risque (retards DPD, analyse vintage, concentration HHI, limites).
- Contrôle de la qualité des données (10 règles automatisées, workflow de résolution).
- Système d'Alerte Précoce (SAP / EWS) identifiant les facteurs de dégradation.
- Simulateur de Stress-Test de portefeuille.
- Analyste IA en langage naturel (NL2SQL sécurisé en lecture seule).
- Générateur de rapports de crédit professionnels en PDF (ReportLab).

---

## 2. ARCHITECTURE TECHNIQUE & STACK

Toute l'application repose sur **Python Flask** côté application web et **Supabase PostgreSQL** pour la base de données. Aucun framework JavaScript complexe (pas de Next.js/React).

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              NAVIGATEUR                                │
 │  HTML5 + Tailwind CSS + Alpine.js + ApexCharts / Lucide                │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / HTMX
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                          APPLICATION FLASK                             │
 │  - App Factory Pattern (Flask Blueprints)                              │
 │  - Engine de Métriques Centralisé (app/metrics.py)                     │
 │  - ORM / Query Builder: SQLAlchemy / psycopg2 / Supabase Python Client │
 │  - Engine PDF: ReportLab + Matplotlib                                  │
 │  - Routeur Analyste IA (SQL Validator + LLM Client)                    │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ SQL (Postgres / Supabase)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                         SUPABASE (POSTGRESQL)                          │
 │  - Tables de faits & dimensions (borrowers, loans, payments, etc.)     │
 │  - Vues SQL d'agrégation (v_loans_enriched, v_kpi_monthly, etc.)       │
 │  - Table d'état applicatif (app_state pour anomalies DQ)               │
 └────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Stack Détaillée

| Composant | Technologie | Rôle / Utilisation |
|---|---|---|
| **Backend Framework** | Python 3.11+ / **Flask** | Routers (Blueprints), logique métier, rendu Jinja2, API endpoints. |
| **Base de Données** | **Supabase (PostgreSQL)** | Stockage relationnel, vues SQL, requêtes d'analyse. |
| **Styling & UI** | **Tailwind CSS (v3 CDN/CLI)** | Thème customisé AuditOS (Couleurs, typographie, ombres). |
| **Interactivité Frontend** | **Alpine.js** (ou HTMX) | Modales, onglets, filtres dynamiques, rechargements légers sans recharger la page. |
| **Data Visualisation** | **ApexCharts.js** ou **Chart.js** | Histrogrammes, donuts, courbes vintage, re-créés selon le design AuditOS. |
| **Icônes** | **Lucide Icons** | Icônes vectorielles épurées (médicales, financières, alertes). |
| **Rapports PDF** | **ReportLab** + Matplotlib | Génération côté serveur des fiches de crédit A4 imprimables en français. |
| **Analyste IA** | Python `openai` / `anthropic` | Generation de requêtes SQL en lecture seule sur les vues Supabase. |

---

## 3. UI/UX DESIGN SYSTEM (FIDÉLITÉ MOCKUP AUDITOS)

L'interface doit reproduire fidèlement l'ambiance visuelle du mockup fourni (`AuditOS`) :

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] CreditRisk360  │  Filtres: [Pays ▼] [Secteur ▼] [Exercice 2026 ▼]   [🔍 Search] [👤 Profile]│
├───────────────────────┼───────────────────────────────────────────────────────────────────┤
│ TRAVAUX D'AUDIT       │ Title: Tableau de bord                                            │
│ 📊 Tableau de bord    ├───────────────────────────────────────────────────────────────────┤
│ 💼 Engagements        │ [Icon] Total Encours   [Icon] NPL Ratio   [Icon] Total Emprunteurs...  │
│ 👥 Clients            │  128.4 Md XAF           6.9 %              12 000                 │
│ 🎯 Risk Analytics     ├───────────────────────────────────┬───────────────────────────────┤
│ 📐 Sampling / Scoring │ Paramètres & Filtres             │ Table / Graphique Principal   │
│ 📁 Qualité Données    │ ┌───────────────────────────────┐ │ ┌───────────────────────────┐ │
│ ⚠️ Alertes (SAP)      │ │ Méthode                       │ │ │ N°  Emprunteur   Statut   │ │
│ 🤖 Analyste IA        │ │ [ Sampling Aléatoire    ▼ ]   │ │ │ 1   SOCAM SA     En cours │ │
│ PARAMÈTRES            │ │ Taux de confiance             │ │ │ 2   ETS BAKO     Terminé  │ │
│ ⚙️ Configuration      │ │ [ 95%                   ▼ ]   │ │ └───────────────────────────┘ │
└───────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

### 3.1 Palette de Couleurs Canoniques
- **Sidebar Background :** `#111827` (Slate/Navy très sombre)
- **Sidebar Text Secondary :** `#9CA3AF` | **Text Active :** `#FFFFFF`
- **Sidebar Active Item Background :** `#5B50E5` (Violet principal AuditOS) avec coins arrondis
- **Canvas Background :** `#F8FAFC` (Gris très clair/frais)
- **Cards Background :** `#FFFFFF` (Blanc pur, border `1px solid #E2E8F0`, rounded `xl` ou `lg`)
- **Accent Purple / Primary Buttons :** `#5B50E5` (Hover: `#4F46E5`)
- **Pastels pour Avatars d'Icônes KPI :**
  - Purple Icon BG: `#EEF2FF` (Text: `#4F46E5`)
  - Green Icon BG: `#ECFDF5` (Text: `#059669`)
  - Blue Icon BG: `#EFF6FF` (Text: `#2563EB`)
  - Amber Icon BG: `#FFFBEB` (Text: `#D97706`)
  - Red Icon BG: `#FEF2F2` (Text: `#DC2626`)
- **Badges de Statut Pastel :**
  - *En attente / Modéré :* BG `#FEF3C7`, Text `#D97706`
  - *En cours / Élevé :* BG `#E0F2FE`, Text `#0284C7`
  - *Terminé / Faible :* BG `#DCFCE7`, Text `#16A34A`
  - *Critique / Très Élevé :* BG `#FEE2E2`, Text `#DC2626`

### 3.2 Typographie & Composants Layout
- **Police :** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, sans-serif.
- **Top Navigation Bar :** Fil d'ariane clair (`Engagements > SOCAM SA > Exercice 2024`), barre de recherche globale, cloche de notifications, avatar utilisateur (`Jean Dupont, Manager`).
- **Cards KPI :** Disposées en grille de 4 à 6 cartes. Icône à gauche encadrée dans un carré pastel arrondi, valeur en gras taille `text-xl` ou `text-2xl`, sous-titre explicatif.
- **Tables :** En-têtes gris clair (`#F8FAFC`), bordures fines, checkboxes de sélection, badges de statut arrondis, menu d'action à droite (`⋮`), pagination en bas à droite (`1 2 3 ... 8`, `10 / page`).

---

## 4. BASE DE DONNÉES SUPABASE (POSTGRESQL) & DONNÉES SYNTHÉTIQUES

Toutes les tables sont hébergées sur Supabase. Un script Python dédié (`seed_supabase.py`) initialise le schéma et injecte des données déterministes (graine fixe = `42`).

### 4.1 Schéma des Tables PostgreSQL (Supabase)

```sql
-- Referentiel Pays ISO Alpha-3 CEMAC
CREATE TABLE countries (
    country_code VARCHAR(3) PRIMARY KEY,
    name_short_fr VARCHAR(50) NOT NULL,
    name_full_fr VARCHAR(100) NOT NULL,
    sort_order INT DEFAULT 0
);

INSERT INTO countries VALUES 
('CMR', 'Cameroun', 'République du Cameroun', 1),
('CAF', 'Centrafrique', 'République centrafricaine', 2),
('COG', 'Congo', 'République du Congo', 3),
('GAB', 'Gabon', 'République gabonaise', 4),
('GNQ', 'Guinée équatoriale', 'République de Guinée équatoriale', 5),
('TCD', 'Tchad', 'République du Tchad', 6);

-- Institutions déclarantes
CREATE TABLE institutions (
    institution_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('BANK', 'MFI')),
    country_hq VARCHAR(3) REFERENCES countries(country_code)
);

-- Emprunteurs
CREATE TABLE borrowers (
    borrower_id VARCHAR(20) PRIMARY KEY,
    borrower_type VARCHAR(20) CHECK (borrower_type IN ('INDIVIDUAL', 'SME', 'CORPORATE')),
    display_name VARCHAR(150) NOT NULL,
    country VARCHAR(3) REFERENCES countries(country_code),
    sector VARCHAR(50) NOT NULL,
    registration_date DATE NOT NULL,
    is_demo BOOLEAN DEFAULT FALSE
);

-- Prêts / Facilités
CREATE TABLE loans (
    loan_id VARCHAR(20) PRIMARY KEY,
    borrower_id VARCHAR(20) REFERENCES borrowers(borrower_id),
    institution_id VARCHAR(10) REFERENCES institutions(institution_id),
    loan_type VARCHAR(50) NOT NULL,
    principal_amount NUMERIC(15, 2) NOT NULL,
    outstanding_amount NUMERIC(15, 2) NOT NULL, -- Encours restant dû (SOURCE DE VÉRITÉ EXPOSITION)
    interest_rate NUMERIC(5, 2) NOT NULL,
    start_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'CLOSED', 'DEFAULTED', 'WRITTEN_OFF')),
    collateral_flag BOOLEAN DEFAULT FALSE,
    restructured_flag BOOLEAN DEFAULT FALSE
);

-- Suivi des remboursements / paiements
CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    loan_id VARCHAR(20) REFERENCES loans(loan_id),
    due_date DATE NOT NULL,
    payment_date DATE,
    amount_due NUMERIC(15, 2) NOT NULL,
    amount_paid NUMERIC(15, 2) NOT NULL,
    days_past_due INT DEFAULT 0
);

-- Table de faits mensuelle pour analyses de cohorte/vintage
CREATE TABLE loan_monthly (
    loan_id VARCHAR(20) REFERENCES loans(loan_id),
    as_of_date DATE NOT NULL,
    outstanding_amount NUMERIC(15, 2) NOT NULL,
    dpd INT DEFAULT 0,
    dpd_bucket VARCHAR(20) NOT NULL,
    PRIMARY KEY (loan_id, as_of_date)
);

-- Consultations / Enquiries
CREATE TABLE enquiries (
    enquiry_id BIGSERIAL PRIMARY KEY,
    borrower_id VARCHAR(20) REFERENCES borrowers(borrower_id),
    institution_id VARCHAR(10) REFERENCES institutions(institution_id),
    enquiry_date DATE NOT NULL,
    purpose VARCHAR(100)
);

-- État applicatif (Gestion du workflow de correction Qualité Données)
CREATE TABLE app_state_dq_resolutions (
    issue_id VARCHAR(50) PRIMARY KEY,
    rule_id VARCHAR(10) NOT NULL,
    record_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'DETECTED' CHECK (status IN ('DETECTED', 'INVESTIGATING', 'RESOLVED')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Vues Métier Sécurisées pour l'Analyste IA et les Dashboards
- `v_loans_enriched` : Jointure `loans` + `borrowers` + `institutions` + `countries`.
- `v_kpi_monthly` : Agrégation par mois de l'encours total, encours NPL, taux de défaut.
- `v_segment_monthly` : Agrégation mensuelle par (Pays x Secteur x Taille).

### 4.3 Règles Métier & Définitions Strictes (Consignes v1.1)

| Indicateur | Formule / Définition Canonique (Fichier `app/metrics.py`) |
|---|---|
| **Exposition** | **Encours restant dû** (`loans.outstanding_amount`), jamais le capital initial. |
| **Ratio NPL** | Encours des prêts avec $DPD \ge 90$ / Encours total des prêts actifs. |
| **Taux de Défaut 12m** | Prêts ayant franchi 90 DPD lors des 12 derniers mois / Prêts actifs il y a 12 mois. |
| **Taux de Paiement** | Somme des montants payés / Somme des montants **échus à la date de référence**. |
| **Dossier Vierge** | $0$ retard sur les 24 derniers mois, aucun impayé, aucun défaut, aucune restructuration. |
| **Date de Référence** | Paramètre unique `AS_OF_DATE = 2026-08-31`. Aucune donnée après cette date. |

---

## 5. SPÉCIFICATIONS DES MODULES FONCTIONNELS

### 5.1 Module 1 : Tableau de Bord Exécutif (`/dashboard`)
- **UI Design AuditOS :**
  - **6 Cartes KPI hautes :** Encours Total (ex: `104.2 Md XAF`), Nombre d'emprunteurs (`12 840`), Prêts actifs (`19 412`), Ratio NPL (`6.8 %`), Taux de défaut 12m (`5.2 %`), Score moyen (`684`).
  - **Graphiques principaux :**
    1. Évolution de l'encours et NPL sur 24 mois (Graphique mixte Barres/Lignes).
    2. Répartition de l'exposition par pays (Cameroun, Tchad, Gabon, etc.) - Barres horizontales.
    3. Répartition de l'exposition par secteur (BTP, Commerce, Industrie, etc.).
    4. Donut Chart de la distribution des bandes de risque (Faible, Modéré, Élevé, Très Élevé).

### 5.2 Module 2 : Fiche Emprunteur 360° (`/borrowers` et `/borrowers/<id>`)
- **Liste des emprunteurs :** Table paginée (20/page) avec filtres par pays, secteur, bande de risque et raccourcis vers **5 profils de démo** (Sain, Sous surveillance, En défaut, Multi-institutions, Nouveau).
- **Fiche Detail :**
  - **En-tête :** Nom, Forme juridique (SARL, SA, Ets), Pays (nom court FR), Secteur, Statut.
  - **Bloc Score Explicable :** Jauge 300-850, bande de risque, et **décomposition en points** (ex: *Historique paiement +42 pts, Utilisation dette -18 pts*).
  - **36 mois d'historique de paiement :** Bandeau mensuel interactif coloré selon le retard DPD avec tooltip d'information.
  - **Bouton d'action :** `[ 📄 Générer Rapport de Crédit PDF ]`.

### 5.3 Module 3 : Risk Analytics (`/risk`)
- **Tranches de Retards (DPD) :** Courant, 1-30 j, 31-60 j, 61-90 j, 90+ j.
- **Analyse Vintage (Cohortes) :** Graphique en lignes montrant le taux de défaut cumulé par mois d'ancienneté (MOB) pour chaque cohorte trimestrielle (2023, 2024, 2025). Heatmap interactive.
- **Concentration & Limites (HHI) :**
  - Calcul de l'indice Herfindahl-Hirschman ($HHI = \sum s_i^2 \times 10\,000$).
  - Tableau de suivi des limites réglementaires (Secteur unique $\le 25\%$, Emprunteur unique $\le 2\%$). Statuts : `OK`, `VIGILANCE`, `DÉPASSEMENT`.

### 5.4 Module 4 : Qualité des Données (`/data-quality`)
- **Score Global DQ :** Moyenne calculée dynamiquement sur 4 dimensions (Complétude, Validité, Unicité, Cohérence).
- **Tableau des 10 Règles Automatisées (DQ-01 à DQ-10) :**
  - Dates manquantes, doublons d'emprunteurs, encours négatifs, échéance antérieure à l'octroi, statut CLOSED avec encours, DPD incohérent, etc.
- **Workflow Interactif :** Cliquer sur une règle $\rightarrow$ Voir les enregistrements défaillants $\rightarrow$ Changer statut (`Investiguer` / `Corriger`) $\rightarrow$ Bouton `[ 🔄 Relancer la validation ]` qui re-calcule les scores en direct.

### 5.5 Module 5 : Système d'Alerte Précoce / SAP (`/alerts`)
- Détection automatique sur les segments (Pays x Secteur x Taille).
- **Génération d'Alertes :** Niveaux `HIGH`, `MEDIUM`, `LOW`.
- **Explication des Drivers (Pourquoi ?) :** Pourcentage explicatif de la dégradation (ex: *45% dû à la dérive des nouveaux prêts < 6 mois, 35% dû aux basculements vers 30+ DPD*).

### 5.6 Module 6 : Générateur de Rapports PDF (`/borrowers/<id>/pdf`)
- Génération côté serveur avec **ReportLab**.
- Format A4 professionnel en Français, incluant :
  - Bandeau aux couleurs AuditOS (`#111827` / `#5B50E5`).
  - Mention obligatoire : **« DONNÉES SYNTHÉTIQUES — RAPPORT DE DÉMONSTRATION »**.
  - Score, facteurs explicatifs, tableau des facilités actives, graphique de paiement Matplotlib incorporé.

### 5.7 Module W1 : Scorecard Explicable (`/scoring`)
- Formule canonique : $Score = 300 + 550 \times \sum (Poids_i \times SousScore_i)$.
- Explication complète des contributions positives et négatives par rapport au profil moyen du portefeuille.

### 5.8 Module W2 : Simulateur de Stress-Test (`/simulator`)
- Modélisation de chocs paramétrables : Choc général de défaut ($0 \text{ à } +100\%$), Hausse des taux ($+1 \text{ à } +5 \text{ pts}$), Choc sectoriel ciblable (ex: BTP $+30\%$).
- Sorties instantanées : Tableau comparatif Base vs Stress (NPL, Perte Attendue / Expected Loss) + Graphique dynamique.

### 5.9 Module W3 : Analyste IA en Langage Naturel (`/analyst`)
- Interface de Chat restreinte au Text-to-SQL.
- **Garde-fous stricts :**
  - Seule la commande `SELECT` est autorisée.
  - Exécution restreinte uniquement sur les vues `v_*`.
  - Pas de requêtes système (`PRAGMA`, `PG_TABLES`, etc.).
  - `LIMIT 500` imposé automatiquement.
  - L'IA explique le résultat en français en $\le 120$ mots en citant exclusivement les chiffres retournés par Supabase.

---

## 6. PLAN D'IMPLÉMENTATION EN PHASES (POUR GLM 5.3 FLASH)

Pour garantir un codage sans erreur par l'agent IA, le développement est découpé en **6 phases séquentielles**. L'agent doit valider chaque phase avant de passer à la suivante.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 0 : Squelette Flask & Config Supabase                              │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1 : Script Seed PostgreSQL & Schéma Supabase                      │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2 : UI Core Framework (Jinja2 Layout & Design System AuditOS)     │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3 : Implémentation des Modules P0 (M1, M2, M3, M4)               │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4 : Moteur PDF & Modules Avancés (M5 SAP, W1 Scoring, W2 Stress) │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 5 : Analyste IA (NL2SQL) & Recette Finale                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### PHASE 0 : Structure du Projet & Configuration
- Structurer l'application Flask avec le pattern **App Factory**.
- Créer le fichier `config.py` gérant les clés Supabase (`SUPABASE_URL`, `SUPABASE_KEY`) et `AS_OF_DATE = "2026-08-31"`.
- Configurer les Blueprints Flask : `main`, `api`, `borrowers`, `risk`, `dq`, `alerts`, `simulator`, `analyst`.

### PHASE 1 : Base de Données Supabase & Script de Seed
- Rédiger le fichier `schema.sql` complet pour Supabase.
- Développer `seed_supabase.py` :
  - Générer déterministement 12 000 emprunteurs, 20 000 prêts, 400 000 paiements.
  - Injecter le scénario S1 (dérive impayés BTP Cameroun), S2 (dépassement limite Tchad), S3 (cohortes 2025).
  - Injecter exactement les anomalies de qualité pour alimenter le module DQ (dates manquantes, doublons, etc.).

### PHASE 2 : Layout HTML/Jinja2 & Design System AuditOS
- Créer `templates/base.html` avec :
  - Sidebar sombre `#111827`, icônes Lucide, navigation active violette `#5B50E5`.
  - Header avec fil d'ariane, barre de recherche, date de référence "Données au 31/08/2026" et badge "Données synthétiques - Démonstration".
  - Inclusion des CDNs : Tailwind CSS, Alpine.js, ApexCharts.

### PHASE 3 : Implémentation des Modules Socles (P0)
- **`app/metrics.py` :** Écrire toutes les fonctions de calcul uniques (Exposition, NPL, Taux de paiement, Dossier vierge).
- **Module M1 (Dashboard) :** Rendu Jinja2 des 6 cartes KPI + intégration ApexCharts.
- **Module M2 (Borrower 360) :** Table des emprunteurs avec pagination, barre de recherche, fiche détail avec historique de paiement interactif.
- **Module M3 (Risk Analytics) :** Graphiques de concentration, calcul HHI, courbes de vintage.
- **Module M4 (Qualité des Données) :** Tableau des 10 règles DQ et routes POST pour corriger/revalider les anomalies.

### PHASE 4 : Rapports PDF & Fonctionnalités Décisionnelles
- **Module M6 (Rapport PDF) :** Créer le service ReportLab générant la fiche A4 complète en français.
- **Module M5 (SAP / Alertes Précoces) :** Moteur de détection de dérives sectorielles + panneau "Pourquoi ?".
- **Module W1 (Scoring) :** Implémentation du moteur de score explicable avec détail des points.
- **Module W2 (Stress-Test) :** Page de simulation avec sliders Alpine.js et recalcul instantané des métriques.

### PHASE 5 : Analyste IA, Polissage & Tests
- **Module W3 (Analyst IA) :** Integration de l'agent SQL sécurisé (parsing `sqlglot` ou regex strict `SELECT ONLY`).
- **Page Méthodologie (T1) :** Documentation complète du dictionnaire de données et des formules.
- **Recette de fin de projet :** Vérification de l'absence de chiffres en dur, vérification du responsive desktop, validation des tests unitaires `pytest`.

---

## 7. EXIGENCES NON FONCTIONNELLES & CONSIGNES DE DÉVELOPPEMENT

1. **Aucun chiffre en dur :** Toutes les valeurs affichées à l'écran doivent provenir de requêtes SQL ou de fonctions du module `app/metrics.py`.
2. **Langue :** Interface utilisateur 100 % en Français. Code source, commentaires et commits Git en Anglais.
3. **Performance :** Vues pré-calculées dans Supabase pour garantir un chargement du tableau de bord < 500 ms.
4. **Sécurité :** Clés d'API stockées uniquement dans `.env` côté serveur Flask.
```

eof
```

---

### Résumé des ajustements effectués pour votre projet :
- **Framework & Dynamic Stack :** Le projet est désormais 100 % Python Flask avec templates Jinja2. L'interactivité est assurée par Alpine.js et ApexCharts sans la complexité d'une SPA React/Next.js.
- **Base de Données :** Intégration complète avec Supabase PostgreSQL via un script de génération/seed automatisé.
- **Design System :** Re-création exacte de l'apparence visuelle d'**AuditOS** (sidebar sombre `#111827`, touche violette `#5B50E5`, cartes épurées, badges pastels, tables paginées avec statut).
- **Consignes de calcul v1.1 :** Application stricte de la date pivot (`31/08/2026`), des codes pays ISO Alpha-3 (`CMR`, `GAB`, etc.) et des règles de calcul financières unifiées.

Vous pouvez directement copier-coller ce cahier des charges et le transmettre à **GLM 5.3 Flash** pour lancer le codage phase par phase !