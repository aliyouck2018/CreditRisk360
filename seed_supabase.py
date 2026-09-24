#!/usr/bin/env python3
"""CreditRisk360 — deterministic synthetic data generator / seeder.

Generates (seed = 42):
  - 12,000 borrowers across CEMAC (CMR, CAF, COG, GAB, GNQ, TCD)
  - ~20,000 loans, ~400,000 monthly payments, 24 months of loan_monthly facts
  - Demo borrower profiles (healthy / watchlist / default / multi-bank / new)
  - Scenario S1 (BTP Cameroun arrears drift), S2 (Tchad concentration breach),
    S3 (worse 2025 cohorts)
  - Planted data-quality anomalies for the DQ module (missing dates, duplicates,
    negative exposure, maturity < start, CLOSED with balance, DPD mismatch,
    future-dated payments, out-of-range rates, missing country, chronology)

Usage:
  python seed_supabase.py [--dsn postgresql://postgres:postgres@localhost:5432/creditrisk360]
"""
import argparse
import calendar
import io
import os
import random
import sys
from datetime import date, timedelta

import psycopg2

AS_OF_DATE = date(2026, 8, 31)
SEED = 42
N_BORROWERS = 12_000
N_LOANS = 20_000

COUNTRIES = [
    ("CMR", "Cameroun", "République du Cameroun", 1),
    ("CAF", "Centrafrique", "République centrafricaine", 2),
    ("COG", "Congo", "République du Congo", 3),
    ("GAB", "Gabon", "République gabonaise", 4),
    ("GNQ", "Guinée équatoriale", "République de Guinée équatoriale", 5),
    ("TCD", "Tchad", "République du Tchad", 6),
]
COUNTRY_WEIGHTS = [0.40, 0.08, 0.12, 0.16, 0.07, 0.17]

INSTITUTIONS = [
    ("BANK-001", "Ecobank Cameroun", "BANK", "CMR"),
    ("BANK-002", "Afriland First Bank", "BANK", "CMR"),
    ("BANK-003", "UBA Cameroun", "BANK", "CMR"),
    ("BANK-004", "BGFI Bank Gabon", "BANK", "GAB"),
    ("BANK-005", "Ecobank Tchad", "BANK", "TCD"),
    ("BANK-006", "BSIC Tchad", "BANK", "TCD"),
    ("BANK-007", "Banque Congolaise de l'Habitat", "BANK", "COG"),
    ("BANK-008", "Ecobank RCA", "BANK", "CAF"),
    ("MFI-001", "Crédit Communautaire Africain", "MFI", "CMR"),
    ("MFI-002", "Express Union", "MFI", "CMR"),
    ("MFI-003", "FINCA RDC-Congo", "MFI", "COG"),
    ("MFI-004", "MicroBanktchad SA", "MFI", "TCD"),
]

SECTORS = [
    "BTP", "Commerce", "Industrie", "Agriculture",
    "Transport", "Services", "Mines & Pétrole", "Télécoms",
]
SECTOR_WEIGHTS = [0.16, 0.24, 0.15, 0.12, 0.10, 0.13, 0.06, 0.04]

LOAN_TYPES = ["Crédit à terme", "Crédit-bail", "Ligne de crédit", "Découvert", "Micro-crédit"]

CORP_PREFIXES = ["ETS", "SARL", "SA", "Groupe", "Société", "Entreprise"]
CORP_ROOTS = [
    "SOCAM", "BTP Sahel", "SONACOM", "COMATEX", "SOTRANS", "AGROTCHEP", "MINEX",
    "MAHOGANY", "COTONEX", "TIMBERCO", "Pétro Invest", "BATIMETAL", "SOCAPALM",
    "NIOTO", "CHEMILOR", "SUDCOM", "LECAMSUD", "SITRABALI", "ALUBASSA",
    "Palmconsum", "TASKAM", "GRAINES DU SAHEL", "FOURNITURES DU BASSIN",
    "TRANS OUBANGUI", "BOIS DU MBAM", "CIMENT DU LOGONE", "TEXTILE KANO",
    "Digital CEMAC", "Netlink Africa", "Sécur自查", "Optima Services",
]
IND_FIRST = [
    "Abdoulaye", "Fatimé", "Jean-Pierre", "Marcel", "Aïcha", "Ousmane", "Nadège",
    "Sylvie", "Mahamat", "Brahim", "Chantal", "Éric", "Rachid", "Noëlle", "Idriss",
    "Amine", "Céline", "Djibril", "Patrice", "Rosalie", "Hamid", "Léa", "Serge",
]
IND_LAST = [
    "Bakari", "Nguema", "Mbala", "Ousmane", "Kolongo", "Djemba", "Sokona",
    "Ngartaba", "Mbefo", "Abakar", "Tolli", "Ndongo", "Bemba", "Goumgou",
    "Sail", "Mbagou", "Koulamoutou", "Tinga", "Greatombo", "Bandjoun",
]

rng = random.Random(SEED)

_used_names = set()
_NAME_VARIANTS = [
    "& Fils", "SARL", "& Co", "International", "SUARL", "Union", "Sud",
    "Nord", "Est", "Ouest", "Centrale", "Atlas", "Sahel", "Group", "CMC", "Inter",
]


def gen_name(btype):
    """Unique display names; natural collisions get a company-style suffix."""
    for _ in range(50):
        if btype == "INDIVIDUAL":
            name = f"{rng.choice(IND_FIRST)} {rng.choice(IND_LAST)}"
        else:
            prefix = rng.choice(CORP_PREFIXES)
            root = rng.choice(CORP_ROOTS)
            if prefix in ("ETS", "Groupe", "Entreprise"):
                name = f"{prefix} {root}"
            else:
                name = f"{root} {prefix}"
        if name not in _used_names:
            _used_names.add(name)
            return name
    # deterministic de-dup suffix
    counter = 2
    candidate = name + f" {counter}"
    while candidate in _used_names:
        counter += 1
        candidate = name + f" {counter}"
    _used_names.add(candidate)
    return candidate


def weighted_choice(options, weights):
    return rng.choices(options, weights=weights, k=1)[0]


def gen_registration_date():
    start = date(2018, 1, 1)
    delta = (AS_OF_DATE - start).days
    return start + timedelta(days=rng.randint(0, delta))


def gen_loan_dates(reg_date):
    """Loan start between 2021-01 and 2026-08, term 1..7 years."""
    lo = max(reg_date, date(2021, 1, 1))
    if lo >= AS_OF_DATE:
        lo = date(2021, 1, 1)
    delta = (AS_OF_DATE - lo).days
    start = lo + timedelta(days=rng.randint(0, delta))
    years = rng.choice([1, 2, 3, 4, 5, 7])
    maturity = date(start.year + years, start.month, 1) - timedelta(days=1)
    return start, maturity


def months_between(d1, d2):
    return max(0, (d2.year - d1.year) * 12 + (d2.month - d1.month))


def month_end(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def add_months(d, n):
    y, m = divmod((d.year * 12 + d.month - 1) + n, 12)
    return date(y, m + 1, 1)


def dpd_bucket(dpd):
    if dpd <= 0:
        return "CURRENT"
    if dpd <= 30:
        return "1-30"
    if dpd <= 60:
        return "31-60"
    if dpd <= 90:
        return "61-90"
    return "90+"


def gen_borrowers():
    borrowers = []
    for i in range(1, N_BORROWERS + 1):
        btype = weighted_choice(
            ["INDIVIDUAL", "SME", "CORPORATE"], [0.72, 0.25, 0.03])
        country = weighted_choice([c[0] for c in COUNTRIES], COUNTRY_WEIGHTS)
        sector = weighted_choice(SECTORS, SECTOR_WEIGHTS)
        borrowers.append({
            "borrower_id": f"BRW{i:06d}",
            "borrower_type": btype,
            "display_name": gen_name(btype),
            "country": country,
            "sector": sector,
            "registration_date": gen_registration_date(),
            "is_demo": False,
        })
    return borrowers


# Demo profiles: explicit, hand-crafted behaviour --------------------------
DEMO_BORROWERS = [
    {"borrower_id": "BRW-DEMO-01", "borrower_type": "CORPORATE",
     "display_name": "SOTRACAM SA", "country": "CMR", "sector": "Transport",
     "registration_date": date(2019, 3, 12), "is_demo": True, "profile": "healthy"},
    {"borrower_id": "BRW-DEMO-02", "borrower_type": "SME",
     "display_name": "Groupe BTP Sahel SARL", "country": "TCD", "sector": "BTP",
     "registration_date": date(2020, 7, 1), "is_demo": True, "profile": "watchlist"},
    {"borrower_id": "BRW-DEMO-03", "borrower_type": "SME",
     "display_name": "ETS BAKO & Fils", "country": "CMR", "sector": "Commerce",
     "registration_date": date(2018, 11, 20), "is_demo": True, "profile": "defaulted"},
    {"borrower_id": "BRW-DEMO-04", "borrower_type": "CORPORATE",
     "display_name": "GAZ Equatorial SA", "country": "GAB", "sector": "Mines & Pétrole",
     "registration_date": date(2017, 5, 2), "is_demo": True, "profile": "multi"},
    {"borrower_id": "BRW-DEMO-05", "borrower_type": "SME",
     "display_name": "NUM Digitale SARL", "country": "COG", "sector": "Télécoms",
     "registration_date": date(2026, 4, 15), "is_demo": True, "profile": "new"},
]


def gen_loans(borrowers):
    loans = []
    n_demo_loans = 0
    # Load borrower list
    b_list = borrowers
    # Assign ~1.6 loans per borrower with repeats
    idx_pool = list(range(len(b_list)))
    for j in range(N_LOANS):
        if j % 3 != 2:  # 2/3 of loans go to a fresh borrower
            b = b_list[rng.randint(0, len(b_list) - 1)]
        else:
            b = b_list[rng.randint(0, len(b_list) - 1)]
        btype = b["borrower_type"]
        if btype == "INDIVIDUAL":
            principal = rng.choice([0.3, 0.6, 1.0, 1.5, 2.5, 4.0]) * 1_000_000 * rng.uniform(0.8, 1.3)
        elif btype == "SME":
            principal = rng.choice([4, 8, 12, 20, 30, 50]) * 1_000_000 * rng.uniform(0.7, 1.3)
        else:  # CORPORATE
            principal = rng.choice([20, 35, 50, 80, 110, 150]) * 1_000_000 * rng.uniform(0.7, 1.4)
        start, maturity = gen_loan_dates(b["registration_date"])
        rate = round(rng.uniform(6.5, 14.5), 2)
        ltype = weighted_choice(LOAN_TYPES, [0.45, 0.12, 0.18, 0.10, 0.15])
        loans.append({
            "loan_id": f"LN{j+1:06d}",
            "borrower_id": b["borrower_id"],
            "institution_id": rng.choice(INSTITUTIONS)[0],
            "loan_type": ltype,
            "principal_amount": round(principal, 2),
            "interest_rate": rate,
            "start_date": start,
            "maturity_date": maturity,
            "status": None,  # decided by behaviour engine
            "collateral_flag": rng.random() < 0.45,
            "restructured_flag": False,
        })
    return loans


def decide_status(loan, borrower):
    """Assign target behaviour profile using cohort + scenario rules."""
    start = loan["start_date"]
    cohort = start.year
    is_corp = borrower["borrower_type"] == "CORPORATE"

    # S3: cohorts 2025 default more frequently
    pd_default = 0.035 if cohort <= 2024 else 0.062
    if is_corp:
        pd_default += 0.02

    # S1: BTP Cameroun recent-origination drift
    is_s1 = (borrower["country"] == "CMR" and borrower["sector"] == "BTP"
             and start >= date(2025, 1, 1))
    if is_s1:
        pd_default += 0.05

    roll = rng.random()
    if roll < pd_default:
        return "DEFAULTED"
    if roll < pd_default + 0.13:
        return "CLOSED"
    if roll < pd_default + 0.13 + 0.03:
        return "WRITTEN_OFF"
    # S1 watch: fresh BTP CMR loans drifting into 30+ DPD
    if is_s1 and start >= AS_OF_DATE - timedelta(days=200) and rng.random() < 0.35:
        return "WATCH_S1"
    if rng.random() < 0.07:
        return "WATCH"
    return "ACTIVE"


def gen_payments_and_monthly(loans, borrowers_by_id):
    payment_rows = []   # (loan_id, due_date, payment_date, amount_due, amount_paid, dpd)
    monthly_rows = []   # (loan_id, as_of_date, outstanding, dpd, bucket)
    window_start = AS_OF_DATE - timedelta(days=731)  # 24 months of facts

    for loan in loans:
        b = borrowers_by_id[loan["borrower_id"]]
        start = loan["start_date"]
        maturity = loan["_maturity"]
        principal = loan["principal_amount"]
        term_m = max(6, months_between(start, maturity) + 1)
        rate = loan["interest_rate"] / 100
        total = principal * (1 + rate * term_m / 12)
        installment = round(total / term_m, 2)

        status_profile = loan["_profile"]
        is_default_profile = status_profile in ("DEFAULTED", "WRITTEN_OFF")
        default_mob = None
        is_closed = status_profile in ("CLOSED", "WRITTEN_OFF")
        months_to_asof = months_between(start, AS_OF_DATE) + 1
        if month_end(start) < AS_OF_DATE:
            n_sched = min(months_to_asof, term_m)
        else:
            n_sched = 0

        # decide default month for DEFAULTED/WRITTEN_OFF
        default_mob = None
        if status_profile in ("DEFAULTED", "WRITTEN_OFF"):
            lo_m = min(6, max(2, n_sched - 2)) if n_sched > 7 else max(2, n_sched - 1)
            if n_sched > 7:
                default_mob = rng.randint(lo_m, n_sched)
            else:
                default_mob = max(1, n_sched - 1)

        # S1 watch loans: recent months drifting 35-75 DPD
        s1_watch = status_profile == "WATCH_S1"
        general_watch = status_profile == "WATCH"

        is_closed = status_profile == "CLOSED"
        closed_early = is_closed and start >= date(2024, 9, 1)

        missed_streak = 0
        dpd_now = 0
        months_paid = 0
        frozen_outstanding = None
        outstanding = round(principal, 2)

        for m in range(n_sched):
            due = add_months(start, m + 1) - timedelta(days=1)
            due = min(due, AS_OF_DATE)
            if due > AS_OF_DATE:
                break
            me = month_end(due)
            frac = min(1.0, (m + 1) / term_m)
            outstanding = round(principal * (1 - 0.95 * frac) + principal * 0.05, 2)

            is_default_month = default_mob is not None and m >= default_mob
            paid_full = True
            pay_date = None
            paid_amt = installment
            late_days = 0

            if is_default_month:
                # instalment unpaid, dpd grows
                paid_full = False
                paid_amt = 0.0
                missed_streak += 1
                dpd_now = max(dpd_now, 30 * missed_streak + rng.randint(0, 9)) if missed_streak else dpd_now
                if frozen_outstanding is None:
                    frozen_outstanding = outstanding
                    dpd_now = max(dpd_now, 95)
            else:
                # healthy behaviour with noise
                r = rng.random()
                if s1_watch and m >= n_sched - 3:
                    late_days = rng.randint(35, 70)
                    paid_full = True
                elif general_watch and m >= n_sched - rng.randint(3, 5) and rng.random() < 0.7:
                    late_days = rng.randint(25, 55)
                    if rng.random() < 0.3:
                        paid_amt = round(installment * rng.uniform(0.55, 0.85), 2)
                        missed_streak = min(missed_streak + 1, 2)
                        dpd_now = max(dpd_now, 30 * missed_streak)
                elif r < 0.04 and status_profile == "ACTIVE":
                    late_days = rng.randint(5, 30)
                elif closed_early and m == n_sched - 1 and rng.random() < 0.5:
                    late_days = rng.randint(10, 40)

                if late_days and paid_full:
                    pay_date = due + timedelta(days=late_days)
                    if late_days > 0:
                        dpd_now = max(dpd_now, min(late_days, 89))
                elif paid_full:
                    pay_date = due + timedelta(days=0 if rng.random() < 0.6 else rng.randint(1, 5))
                    if missed_streak:
                        dpd_now = max(0, dpd_now)
                    else:
                        dpd_now = 0
                if paid_full and pay_date and pay_date <= me and missed_streak == 0 and late_days < 25:
                    dpd_now = 0

            if is_default_month and frozen_outstanding is not None:
                outstanding = frozen_outstanding

            # keep the dataset strictly as-of the reference date
            if pay_date and pay_date > AS_OF_DATE:
                pay_date = AS_OF_DATE

            payment_rows.append((
                loan["loan_id"], due, pay_date, installment,
                paid_amt if paid_full else round(paid_amt, 2),
                max(0, (pay_date - due).days) if pay_date else (dpd_now if not paid_full else 0),
            ))

            bucket = dpd_bucket(dpd_now)
            monthly_rows.append((loan["loan_id"], me, outstanding, dpd_now, bucket))
            if not is_default_month and paid_full:
                months_paid += 1

        # final loan status
        if status_profile in ("DEFAULTED", "WRITTEN_OFF"):
            loan["status"] = "DEFAULTED" if status_profile == "DEFAULTED" else "WRITTEN_OFF"
            loan["outstanding_amount"] = frozen_outstanding or outstanding
        elif is_closed:
            loan["status"] = "CLOSED"
            loan["outstanding_amount"] = 0.0
        else:
            loan["status"] = "ACTIVE"
            loan["outstanding_amount"] = outstanding
        if status_profile in ("WATCH", "WATCH_S1"):
            loan["restructured_flag"] = rng.random() < 0.25

    return payment_rows, monthly_rows


def plant_dq_anomalies(loans, borrowers, payment_rows, monthly_rows, borrowers_by_id):
    """Mutate rows to plant the 10 DQ rule violations."""
    # DQ-01: missing dates on loans (start/maturity NULL)
    for l in rng.sample(loans[200:800], 8):
        l["start_date"] = None
    for l in rng.sample(loans[800:1400], 6):
        l["maturity_date"] = None

    # DQ-09: borrowers missing registration date and country
    for b in rng.sample(borrowers[100:600], 10):
        b["registration_date"] = None
    for b in rng.sample(borrowers[600:1100], 12):
        b["country"] = None

    # DQ-03: negative outstanding on some ACTIVE loans
    for l in rng.sample([x for x in loans if x.get("status") == "ACTIVE"], 7):
        l["outstanding_amount"] = -round(max(1, l["principal_amount"]) * rng.uniform(0.01, 0.2), 2)

    # DQ-04: maturity before start
    for l in rng.sample(loans[1500:2200], 6):
        if l["start_date"] and l["maturity_date"]:
            l["maturity_date"] = l["start_date"] - timedelta(days=rng.randint(30, 400))

    # DQ-05: CLOSED with residual outstanding
    closed = [x for x in loans if x.get("status") == "CLOSED"]
    for l in rng.sample(closed, min(9, len(closed))):
        l["outstanding_amount"] = round(l["principal_amount"] * rng.uniform(0.05, 0.3), 2)

    # DQ-06: DPD incoherences in loan_monthly
    for (lid, me, out, dpd, bucket) in monthly_rows[:]:
        if rng.random() < 0.0004 and bucket == "CURRENT":
            # dpd > 0 but bucket says CURRENT
            idx = monthly_rows.index((lid, me, out, dpd, bucket))
            monthly_rows[idx] = (lid, me, out, rng.randint(15, 120), "CURRENT")

    # DQ-07: future-dated payments (beyond AS_OF_DATE)
    planted = 0
    for i in rng.sample(range(1000, len(payment_rows) - 1000), 200):
        row = list(payment_rows[i])
        if row[2] and planted < 12:
            row[2] = AS_OF_DATE + timedelta(days=rng.randint(1, 60))
            row[5] = 0
            payment_rows[i] = tuple(row)
            planted += 1

    # DQ-08: interest rates out of range
    for l in rng.sample(loans[2500:3200], 8):
        l["interest_rate"] = rng.choice([0.0, -2.0, 55.0, 120.0])

    # DQ-02: duplicate borrowers (same name, new IDs)
    dups = []
    sources = rng.sample(borrowers[2000:9000], 15)
    for s in sources:
        d = dict(s)
        d["borrower_id"] = "BRW" + str(rng.randint(990001, 999999))
        d["registration_date"] = s["registration_date"]
        dups.append(d)
    borrowers.extend(dups)

    # DQ-10: loan starting before borrower registration (chronology)
    for l in rng.sample(loans[3300:4000], 8):
        b = borrowers_by_id[l["borrower_id"]]
        if b["registration_date"] and l["start_date"]:
            # move loan start BEFORE registration
            earlier = b["registration_date"] - timedelta(days=rng.randint(90, 500))
            l["start_date"] = earlier
            l["maturity_date"] = earlier + timedelta(days=rng.randint(500, 1500))
    return loans


def add_demo_loans_data(demo_loans, demos, borrowers_by_id):
    """Build rich 36-month histories for the 5 demo borrowers."""
    payment_rows, monthly_rows = [], []
    profiles = {d["borrower_id"]: d["profile"] for d in demos}
    for loan in demo_loans:
        profile = profiles[loan["borrower_id"]]
        start = loan["start_date"]
        maturity = loan["_maturity"]
        principal = loan["principal_amount"]
        term_m = max(6, months_between(start, maturity) + 1)
        rate = loan["interest_rate"] / 100
        total = principal * (1 + rate * term_m / 12)
        installment = round(total / term_m, 2)
        months_to_asof = months_between(start, AS_OF_DATE)
        n_sched = min(months_to_asof, term_m)

        missed_streak = 0
        dpd_now = 0
        last_outstanding = principal
        for m in range(n_sched):
            due = min(add_months(start, m + 1) - timedelta(days=1), AS_OF_DATE)
            me = month_end(due)
            frac = min(1.0, (m + 1) / term_m)
            outstanding = round(principal * (1 - 0.95 * frac) + principal * 0.05, 2)
            pay_date = due
            paid_amt = installment
            late_days = 0

            if profile == "defaulted" and m >= n_sched - 4:
                # last 4 months unpaid, dpd ramping past 90
                missed_streak += 1
                dpd_now = 30 * missed_streak + 5
                paid_amt = 0.0
                pay_date = None
                outstanding = round(principal * (1 - 0.95 * (n_sched - 4) / term_m), 2)
            elif profile == "watchlist" and m >= max(0, n_sched - 6):
                late_days = rng.randint(25, 55)
                pay_date = due + timedelta(days=late_days)
                dpd_now = min(late_days, 60)
                if rng.random() < 0.4:
                    paid_amt = round(installment * 0.75, 2)
            elif profile == "new" and rng.random() < 0.18:
                late_days = rng.randint(2, 12)
                pay_date = due + timedelta(days=late_days)
                dpd_now = late_days
            elif profile == "multi" and rng.random() < 0.25:
                late_days = rng.randint(3, 18)
                pay_date = due + timedelta(days=late_days)
                dpd_now = late_days
            else:
                dpd_now = 0
                pay_date = due + timedelta(days=rng.choice([0, 0, 1, 2]))

            payment_rows.append((loan["loan_id"], due, pay_date, installment,
                                 paid_amt, max(0, (pay_date - due).days) if pay_date else dpd_now))
            monthly_rows.append((loan["loan_id"], me, outstanding, dpd_now, dpd_bucket(dpd_now)))
            last_outstanding = outstanding

        if profile == "defaulted":
            loan["status"] = "DEFAULTED"
            loan["outstanding_amount"] = last_outstanding
        elif profile == "watchlist":
            loan["status"] = "ACTIVE"
            loan["outstanding_amount"] = last_outstanding
            loan["restructured_flag"] = False
        elif profile == "new":
            loan["status"] = "ACTIVE"
            loan["outstanding_amount"] = last_outstanding
        else:
            loan["status"] = "ACTIVE"
            loan["outstanding_amount"] = last_outstanding
    return payment_rows, monthly_rows, demo_loans


def S2_single_borrower_and_concentration(borrowers, loans):
    """S2: Tchad Mines&Pétrole concentration + one borrower > 2% portfolio."""
    # create one big corporate borrower in TCD exceeding 2% of portfolio
    big = {"borrower_id": "BRW-DEMO-06", "borrower_type": "CORPORATE",
           "display_name": "Pétro Invest Tchad SA", "country": "TCD",
           "sector": "Mines & Pétrole", "registration_date": date(2019, 2, 4),
           "is_demo": True, "profile": "healthy"}
    borrowers.append(big)
    loans.append({
        "loan_id": "LN900001", "borrower_id": big["borrower_id"],
        "institution_id": "BANK-005", "loan_type": "Crédit à terme",
        "principal_amount": 3_500_000_000.0, "interest_rate": 8.75,
        "start_date": date(2023, 3, 1), "maturity_date": date(2029, 3, 1),
        "status": "ACTIVE", "collateral_flag": True, "restructured_flag": False,
        "outstanding_amount": 3_100_000_000.0,
    })


def build_demo_loans():
    profiles = {d["borrower_id"]: d["profile"] for d in DEMO_BORROWERS}
    demo_loans = []
    # multi-institution borrower gets 3 loans from different banks
    demo = [
        ("LN-DM-001", "BRW-DEMO-01", "BANK-001", "Crédit à terme", 450_000_000, "healthy"),
        ("LN-DM-002", "BRW-DEMO-02", "BANK-005", "Crédit à terme", 120_000_000, "watchlist"),
        ("LN-DM-003", "BRW-DEMO-03", "BANK-001", "Ligne de crédit", 80_000_000, "defaulted"),
        ("LN-DM-004", "BRW-DEMO-04", "BANK-004", "Crédit-bail", 600_000_000, "multi"),
        ("LN-DM-005", "BRW-DEMO-04", "BANK-001", "Crédit à terme", 250_000_000, "multi"),
        ("LN-DM-006", "BRW-DEMO-04", "MFI-001", "Découvert", 90_000_000, "multi"),
        ("LN-DM-007", "BRW-DEMO-05", "BANK-007", "Crédit à terme", 35_000_000, "new"),
    ]
    for lid, bid, inst, ltype, principal, profile in demo:
        if profile == "new":
            start = date(2026, 4, 20)
            maturity = date(2028, 4, 20)
        elif profile == "defaulted":
            start = date(2023, 6, 1)
            maturity = date(2027, 6, 1)
        elif profile == "watchlist":
            start = date(2023, 1, 15)
            maturity = date(2027, 1, 15)
        elif profile == "multi":
            start = date(2022, 5, 1)
            maturity = date(2028, 5, 1)
        else:
            start = date(2022, 8, 1)
            maturity = date(2027, 8, 1)
        demo_loans.append({
            "loan_id": lid, "borrower_id": bid,
            "institution_id": "BANK-004" if bid == "BRW-DEMO-04" else "BANK-001",
            "loan_type": ltype, "principal_amount": float(principal),
            "interest_rate": round(rng.uniform(7.0, 13.0), 2),
            "start_date": start, "maturity_date": maturity,
            "status": "ACTIVE", "collateral_flag": True, "restructured_flag": False,
            "_maturity": maturity, "_profile": profile,
        })
    return demo_loans


def copy_table(cur, table, columns, rows, fmt_map=None):
    """Bulk COPY rows into table using CSV format."""
    if not rows:
        return
    buf = io.StringIO()
    for row in rows:
        vals = []
        for v in row:
            if v is None:
                vals.append("")
            else:
                vals.append(str(v))
        # naive CSV escaping
        line = ",".join('"' + v.replace('"', '""') + '"' if "," in v or '"' in v else v
                        for v in vals)
        buf.write(line + "\n")
    buf.seek(0)
    cur.copy_expert(
        f"COPY {table} ({','.join(columns)}) FROM STDIN WITH CSV", buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/creditrisk360"))
    args = ap.parse_args()
    rng.seed(SEED)

    conn = psycopg2.connect(args.dsn)
    cur = conn.cursor()

    print("Seeding referential: countries & institutions ...")
    cur.execute("TRUNCATE app_state_dq_resolutions, enquiries, loan_monthly, payments, loans, borrowers, institutions, countries RESTART IDENTITY CASCADE;")
    for c in COUNTRIES:
        cur.execute(
            "INSERT INTO countries VALUES (%s,%s,%s,%s)", c)
    for i in INSTITUTIONS:
        cur.execute("INSERT INTO institutions VALUES (%s,%s,%s,%s)", i)

    print("Generating borrowers ...")
    borrowers = gen_borrowers()
    borrowers += [dict(d) for d in DEMO_BORROWERS]

    print("Generating loans ...")
    loans = gen_loans(borrowers)

    # attach borrower info and maturity
    borrowers_by_id = {b["borrower_id"]: b for b in borrowers}
    for l in loans:
        l["_maturity"] = l["maturity_date"] if l["maturity_date"] else AS_OF_DATE

    print("Assigning behaviour profiles ...")
    for l in loans:
        if l["borrower_id"].startswith("BRW-DEMO"):
            continue  # demo loans carry their profile already
        b = borrowers_by_id[l["borrower_id"]]
        btype = b["borrower_type"]
        cohort = l["start_date"].year if l["start_date"] else 2024
        pd_default = 0.012 if cohort <= 2024 else 0.028
        if btype == "CORPORATE":
            pd_default += 0.008
        is_s1 = (b["country"] == "CMR" and b["sector"] == "BTP"
                 and l["start_date"] and l["start_date"] >= date(2025, 1, 1))
        if is_s1:
            pd_default += 0.05
        roll = rng.random()
        if roll < pd_default:
            l["_profile"] = "DEFAULTED"
        elif roll < pd_default + 0.13:
            l["_profile"] = "CLOSED"
        elif roll < pd_default + 0.145:
            l["_profile"] = "WRITTEN_OFF"
        elif (is_s1 and l["start_date"] >= AS_OF_DATE - timedelta(days=200)
              and rng.random() < 0.35):
            l["_profile"] = "WATCH_S1"
        elif rng.random() < 0.07:
            l["_profile"] = "WATCH"
        else:
            l["_profile"] = "ACTIVE"

    non_demo = [l for l in loans if not l["borrower_id"].startswith("BRW-DEMO")]
    demo_loans = build_demo_loans()

    print("Applying S2 (Tchad concentration) ...")
    S2_single_borrower_and_concentration(borrowers, non_demo)
    borrowers_by_id["BRW-DEMO-06"] = borrowers[-1]
    ln9 = [l for l in non_demo if l["loan_id"] == "LN900001"][0]
    ln9["_maturity"] = ln9["maturity_date"]
    ln9["_profile"] = "ACTIVE"

    print("Generating payments & monthly facts ...")
    payment_rows, monthly_rows = gen_payments_and_monthly(non_demo, borrowers_by_id)
    dpay_rows, dm_rows, demo_loans = add_demo_loans_data(demo_loans, DEMO_BORROWERS, borrowers_by_id)

    print("Planting DQ anomalies ...")
    plant_dq_anomalies(non_demo, borrowers, payment_rows, monthly_rows, borrowers_by_id)
    # inflate remaining TCD Mines&Pétrole outstanding to breach the 25% limit
    tcd_active = [l for l in non_demo
                  if borrowers_by_id[l["borrower_id"]]["country"] == "TCD"
                  and l.get("status") == "ACTIVE"]
    tcd_mines = [l for l in tcd_active
                 if borrowers_by_id[l["borrower_id"]]["sector"] == "Mines & Pétrole"]
    tcd_others = [l for l in tcd_active
                  if borrowers_by_id[l["borrower_id"]]["sector"] != "Mines & Pétrole"]
    mines_sum = sum(l["outstanding_amount"] for l in tcd_mines)
    others_sum = sum(l["outstanding_amount"] for l in tcd_others)
    target_mines = others_sum * 0.36  # → 26.5% share among active TCD
    if mines_sum > 0 and mines_sum < target_mines:
        k = target_mines / mines_sum
        for l in tcd_mines:
            l["outstanding_amount"] = round(l["outstanding_amount"] * k, 2)
        # scale S2 monthly facts for those loans
        s2_ids = {l["loan_id"] for l in tcd_mines}
        monthly_rows = [
            (lid, me, round(out * k, 2) if lid in s2_ids else out, dpd, bucket)
            for (lid, me, out, dpd, bucket) in monthly_rows]

    all_loans = non_demo + demo_loans

    print("Generating enquiries ...")
    enquiry_rows = []
    for b in rng.sample(borrowers, 8_000):
        for _ in range(rng.randint(1, 3)):
            ed = AS_OF_DATE - timedelta(days=rng.randint(1, 900))
            enquiry_rows.append((b["borrower_id"], rng.choice(INSTITUTIONS)[0],
                                 ed, rng.choice([
                                     "Demande de crédit", "Renouvellement ligne",
                                     "Réaménagement", "Suivi portefeuille"])))

    print("Inserting rows via COPY ...")
    copy_table(cur, "borrowers",
               ["borrower_id", "borrower_type", "display_name", "country",
                "sector", "registration_date", "is_demo"],
               [(b["borrower_id"], b["borrower_type"], b["display_name"],
                 b["country"], b["sector"], b["registration_date"], b["is_demo"])
                for b in borrowers])
    copy_table(cur, "loans",
               ["loan_id", "borrower_id", "institution_id", "loan_type",
                "principal_amount", "outstanding_amount", "interest_rate",
                "start_date", "maturity_date", "status", "collateral_flag",
                "restructured_flag"],
               [(l["loan_id"], l["borrower_id"], l["institution_id"], l["loan_type"],
                 l["principal_amount"],
                 l.get("outstanding_amount") if l.get("outstanding_amount") is not None
                 else l["principal_amount"],
                 l["interest_rate"], l["start_date"], l["maturity_date"],
                 l.get("status") or "ACTIVE", l["collateral_flag"],
                 l["restructured_flag"])
                for l in non_demo + demo_loans])
    copy_table(cur, "payments",
               ["loan_id", "due_date", "payment_date", "amount_due",
                "amount_paid", "days_past_due"],
               payment_rows + dpay_rows)
    copy_table(cur, "loan_monthly",
               ["loan_id", "as_of_date", "outstanding_amount", "dpd", "dpd_bucket"],
               monthly_rows + dm_rows)
    copy_table(cur, "enquiries",
               ["borrower_id", "institution_id", "enquiry_date", "purpose"],
               enquiry_rows)

    # a couple of pre-resolved DQ workflow examples
    cur.execute("INSERT INTO app_state_dq_resolutions VALUES ('ISS-EX-001','DQ-03','LN000105','RESOLVED',CURRENT_TIMESTAMP), ('ISS-EX-002','DQ-05','LN000288','RESOLVED',CURRENT_TIMESTAMP);")

    conn.commit()

    # summary
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(outstanding_amount),0) FROM loans WHERE status='ACTIVE';
    """)
    n_active, expo = cur.fetchone()
    expo = float(expo)
    cur.execute("""
        SELECT COALESCE(SUM(outstanding_amount),0) FROM loans WHERE status IN ('DEFAULTED','WRITTEN_OFF');
    """)
    npl = float(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM payments")
    npay = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM loan_monthly")
    nmon = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM borrowers")
    nbor = cur.fetchone()[0]
    ratio = (npl / expo * 100) if expo else 0
    print(f"\n=== SEED SUMMARY ===")
    print(f"borrowers      : {nbor:>7,}")
    print(f"loans (total)  : {len(non_demo)+len(demo_loans):>7,}")
    print(f"active loans   : {n_active:>7,}   exposure: {expo/1e9:8.2f} Md XAF")
    print(f"payments       : {npay:>7,}")
    print(f"loan_monthly   : {nmon:>7,}")
    print(f"NPL exposure   : {npl/1e9:8.2f} Md XAF  ratio: {ratio:5.2f}%")
    conn.commit()
    cur.close()
    conn.close()
    print("Seed complete.")


if __name__ == "__main__":
    sys.exit(main())
