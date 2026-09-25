# CREDITRISK360 — DASHBOARD REFACTOR / UX & DATA ANALYTICS PROMPT

## Role

You are a senior Data Analytics product designer, banking analytics expert, and frontend engineer.

You are working on **CreditRisk360**, a portfolio project designed to demonstrate Data Analytics capabilities applied to credit risk and banking.

The objective is NOT to turn the dashboard into a commercial banking core system.

The objective is to make the dashboard look and behave like a convincing **Credit Risk Analytics dashboard built by a Data Analyst**, where the data tells a coherent business story.

---

# 1. IMPORTANT — AUDIT BEFORE MODIFYING

Before writing code, inspect the existing project thoroughly.

Identify:

* current Dashboard page/component
* existing database/data model
* available datasets
* available KPIs
* existing SQL queries
* existing views
* existing charts
* existing filters
* existing API endpoints
* existing TypeScript types/interfaces
* existing design system/components
* existing methodology definitions

Pay particular attention to the methodology page and make sure the Dashboard uses the SAME definitions and calculations.

Do NOT create new metrics simply because they would look good visually.

Do NOT invent data.

Do NOT invent database columns.

Do NOT invent business rules.

If a desired visualization cannot be implemented from the existing data, either:

1. derive it legitimately from existing data, or
2. omit it.

---

# 2. CORE OBJECTIVE

Redesign the Dashboard around four business questions:

### 1. What is the current health of the portfolio?

### 2. How is portfolio risk evolving?

### 3. Where is the risk concentrated?

### 4. What should an analyst investigate next?

The dashboard should feel like an analytical workspace rather than a collection of charts.

The user should understand the overall portfolio within approximately 30 seconds.

---

# 3. RECOMMENDED INFORMATION ARCHITECTURE

Implement the following hierarchy where supported by the existing data.

---

## SECTION 1 — DASHBOARD HEADER

Create a clean executive header.

Suggested structure:

Credit Risk Dashboard

Portfolio overview and risk monitoring

Include:

* analysis period
* last data update if available
* relevant filters

Do not overload the header.

---

# 4. GLOBAL FILTERS

Create a consistent filter area.

Use only dimensions that actually exist in the data.

Potential filters include:

* Period
* Segment
* Region
* Product
* Loan Status
* Risk Category

Only implement filters supported by the existing data model.

Filters should update the relevant dashboard components consistently.

If the current application already has global filtering infrastructure, reuse it instead of creating a parallel system.

---

# 5. EXECUTIVE SNAPSHOT

Create a compact KPI section.

Target:

4–6 KPI cards maximum.

Prioritize metrics already documented in the methodology.

Possible metrics include:

* Total Exposure
* Outstanding Exposure
* NPL Ratio
* Default Rate
* Payment Rate
* Average Risk Score

Use the actual metrics available in the application.

Each KPI should contain:

* metric name
* value
* short contextual description
* optional trend/change indicator when a valid comparison period exists

Avoid decorative metrics.

The KPI section should answer:

> "How healthy is this portfolio?"

---

# 6. PORTFOLIO TREND

Create a major time-series visualization.

The purpose is to answer:

> "Is the portfolio improving or deteriorating?"

Use available monthly/periodic data.

Potential metrics:

* Exposure
* Outstanding balance
* NPL
* Default rate
* Payment rate

Do not put too many metrics into one chart.

Prefer a clear primary trend with optional metric switching if appropriate.

The chart must have:

* clear axis labels
* meaningful XAF formatting
* useful tooltips
* appropriate number formatting
* readable dates
* responsive behavior

Avoid excessive visual decoration.

---

# 7. PORTFOLIO RISK DISTRIBUTION

Create a section showing the distribution of portfolio quality.

If supported by the existing data, use categories such as:

* Current
* 1–30 DPD
* 31–60 DPD
* 61–90 DPD
* 90+ DPD

Use terminology consistently with the methodology.

The objective is to make portfolio deterioration visually obvious.

A user should immediately understand:

> "How much of the portfolio is performing normally versus showing signs of stress?"

---

# 8. WHERE IS THE RISK?

Create a dedicated analytical section.

Use the dimensions that actually exist in the database.

Potential dimensions:

* Segment
* Region
* Product
* Branch
* Borrower type

For each dimension, show appropriate metrics such as:

* Exposure
* Number of loans
* NPL
* Default rate
* Average risk score

Do NOT create five nearly identical charts.

Choose visualizations based on the analytical question.

Examples:

### Risk by Segment

A bar chart comparing exposure and/or NPL.

### Risk by Region

A ranked bar chart or other appropriate visualization.

### Risk by Product

Use only if the underlying data supports it.

The goal is to answer:

> "Where is the risk concentrated?"

---

# 9. CONCENTRATION ANALYSIS

If concentration metrics already exist in CreditRisk360, expose them clearly.

Possible metrics:

* HHI
* Top borrower exposure
* Top 5 / Top 10 borrower concentration
* Segment concentration

Do not present HHI as an abstract mathematical number only.

Explain its business meaning in plain language.

For example:

"Portfolio concentration indicates how dependent the portfolio is on a relatively small number of exposures."

Use the exact methodology already implemented by the application.

---

# 10. RISK SIGNALS / EARLY WARNING

Create a compact section called:

Risk Signals

Show meaningful risk indicators detected from the portfolio.

Possible signals, ONLY if supported by the existing logic:

* increasing delinquency
* high DPD
* elevated NPL
* concentration
* deteriorating payment performance
* high-risk borrower concentration

Each signal should contain:

* title
* severity/status
* short explanation
* optional affected segment/count/exposure
* link to the relevant analytical page where appropriate

Example structure:

RISK SIGNAL

Elevated delinquency in SME portfolio

31–60 DPD exposure increased during the selected period.

View Risk Analytics →

Do not invent thresholds.

Use existing business rules whenever they exist.

---

# 11. ANALYTICAL OBSERVATIONS

Add a section near the bottom:

## Portfolio Observations

This is important.

The dashboard should not only visualize data.

It should help demonstrate analytical thinking.

Generate concise observations dynamically from the available data.

Examples of acceptable patterns:

* "Corporate borrowers represent X% of total exposure."
* "NPL exposure is concentrated in X segment."
* "Payment performance changed by X percentage points during the selected period."
* "The top X borrowers account for X% of portfolio exposure."

Only generate statements that can be calculated directly from the data.

Never fabricate narrative insights.

If dynamic insight generation already exists elsewhere in the application, reuse it where appropriate.

---

# 12. INVESTIGATION FLOW

The dashboard should naturally lead users toward deeper analysis.

Add contextual navigation such as:

* View Risk Analytics
* Explore Clients
* Review Alerts
* Examine Scoring
* Run Stress Test
* Ask AI Analyst

Only expose destinations that actually exist.

The dashboard should function as the entry point into the rest of CreditRisk360.

---

# 13. UX PRINCIPLES

The dashboard must prioritize:

### Clarity

A non-specialist should understand what the major metrics represent.

### Hierarchy

The most important information must visually dominate.

### Analytical usefulness

Every chart must answer a question.

### Consistency

Use the same metric definitions as `/methodology`.

### Restraint

Avoid excessive cards, gradients, shadows, decorative charts, and unnecessary animations.

### Professional banking aesthetic

The interface should feel appropriate for:

* banking
* risk management
* financial analysis
* BI / analytics

But it should NOT look like a generic fintech marketing website.

---

# 14. VISUAL DESIGN

Inspect the existing design system before changing anything.

Preserve:

* existing typography
* color system
* spacing system
* reusable UI components
* navigation
* icons

Improve them only when necessary.

Use color semantically.

For example:

* neutral → normal information
* warning → elevated risk
* critical → significant risk
* positive → improvement

Do not use color merely for decoration.

Charts should be visually coherent with the rest of CreditRisk360.

---

# 15. DATA VISUALIZATION PRINCIPLES

Use appropriate chart types.

Prefer:

* line charts for trends
* horizontal bars for rankings
* stacked bars for composition
* area charts only when composition/volume benefits from them
* tables for detailed borrower-level information
* progress indicators for simple ratios

Avoid:

* 3D charts
* pie charts with many categories
* gauges unless there is a strong analytical reason
* decorative donut charts
* charts with too many series

Format monetary values appropriately.

The project uses XAF/CFA context.

Use readable abbreviations where appropriate:

1.2B XAF
850M XAF
42.5M XAF

But ensure tooltips provide precise values.

---

# 16. RESPONSIVENESS

The dashboard must work properly on:

* desktop
* laptop
* tablet
* smaller screens

Prioritize desktop because this is an analytics application, but do not allow mobile layouts to break.

Charts must resize correctly.

Avoid horizontal overflow.

---

# 17. ACCESSIBILITY

Ensure:

* readable contrast
* semantic headings
* accessible interactive controls
* keyboard navigation where applicable
* meaningful chart labels
* non-color-only indicators

Do not rely exclusively on red/green colors to communicate risk.

---

# 18. PERFORMANCE

Do not introduce unnecessary dependencies.

Reuse existing charting libraries and components.

Avoid duplicated database queries.

If multiple dashboard components request the same data, consider whether the existing architecture can efficiently reuse the result.

Do not prematurely introduce complex state-management architecture.

---

# 19. IMPORTANT — NO FAKE ANALYTICS

This is a portfolio project.

Its credibility depends on analytical integrity.

Therefore:

NEVER:

* invent numbers
* hard-code fake KPI values
* create fake trends
* fabricate alerts
* invent risk categories
* invent thresholds
* invent borrower behavior
* create charts that do not correspond to the underlying data

Every displayed analytical value must ultimately come from the application's actual dataset or a legitimate calculation based on it.

---

# 20. PRESERVE THE METHODOLOGY

The Dashboard and `/methodology` must agree.

For example, if `/methodology` defines:

NPL Ratio = NPL Exposure / Total Exposure

then the Dashboard must use exactly that definition.

If the existing implementation uses a specific scoring formula, DPD classification, default definition, or concentration calculation, preserve it.

Do not silently redefine metrics.

---

# 21. PORTFOLIO POSITIONING

Remember that CreditRisk360 is primarily a:

DATA ANALYTICS PORTFOLIO PROJECT

It demonstrates:

* SQL
* data modeling
* KPI design
* financial analysis
* credit risk analysis
* data visualization
* data quality
* analytical reasoning
* dashboard design
* AI-assisted analytics

The Dashboard should therefore showcase analytical thinking rather than simply looking visually impressive.

---

# 22. IMPLEMENTATION PROCESS

Follow this sequence:

### Step 1

Audit the existing Dashboard.

### Step 2

Audit the underlying data and existing analytical queries.

### Step 3

Map available data to the proposed dashboard sections.

### Step 4

Identify which proposed sections can be implemented without modifying the data model.

### Step 5

Implement the dashboard incrementally.

### Step 6

Validate every KPI against the underlying data.

### Step 7

Check consistency with `/methodology`.

### Step 8

Test filters.

### Step 9

Test responsive behavior.

### Step 10

Remove redundant or decorative visualizations.

### Step 11

Run the application and inspect the final dashboard visually.

### Step 12

Fix any UX inconsistencies before considering the task complete.

---

# 23. FINAL QUALITY CHECK

Before finishing, verify:

* [ ] No fabricated metrics
* [ ] No fabricated data
* [ ] No contradictory methodology
* [ ] KPI calculations are correct
* [ ] Filters work correctly
* [ ] Charts use real application data
* [ ] XAF formatting is consistent
* [ ] Risk terminology is consistent
* [ ] Dashboard tells a coherent story
* [ ] Visual hierarchy is clear
* [ ] Dashboard is not overcrowded
* [ ] Responsive layout works
* [ ] Existing application navigation remains functional
* [ ] No unrelated pages/features were broken

The final result should make a recruiter, Data Analyst, BI Manager, Risk Analyst, or banking professional think:

"This person understands how to move from raw financial data to meaningful analytical insights."

Do not optimize for visual complexity.

Optimize for **clarity, analytical reasoning, credibility, and business usefulness**.