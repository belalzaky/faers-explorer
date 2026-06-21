# FAERS Explorer

Exploring the FDA Adverse Event Reporting System (FAERS) with Python — to understand what pharmacovigilance data can and cannot tell us.

**FAERS** is a public US database of adverse drug event reports submitted by patients, doctors, and manufacturers to the FDA. It contains tens of millions of reports going back to 1968 (via the legacy AERS system) and is one of the most widely used datasets in real-world drug safety research.

> First-year Pharmacology student at King's College London, building data skills in public.
> Write-ups: [belalzaky.substack.com](https://belalzaky.substack.com) · [LinkedIn](https://www.linkedin.com/in/belalzaky)

---

## What I explored

### 1. Most-reported adverse reactions across all of FAERS — `explore.py`
Queried the entire database to find the ten reaction terms that appear most often across all drugs and all years.

**Key finding:** "Drug Ineffective" ranks #1 with 1.28 million reports — ahead of Death, Nausea, and Pain. This is **reporting bias**: people file adverse event reports most often when a drug stops working, not when they experience the expected side effects of taking it. The top-ten list reflects what motivates someone to report, not what hurts the most.

---

### 2. Most-reported drugs across all of FAERS — `top_drugs.py`
Counted which drug names appear most frequently as the suspect drug across all reports.

**Key finding:** Humira and Enbrel (both injectable biologics for autoimmune disease) lead by a wide margin. High report counts are driven by three overlapping factors: **exposure** (widely prescribed drugs accumulate more reports by volume), **monitoring intensity** (biologics are watched more closely than generic pills), and **one-off events** (Zantac sits at #4 largely due to a single contamination recall). A high rank here says nothing about a drug being more dangerous than a lower-ranked one.

---

### 3. One drug's reaction profile — `humira_reactions.py`
Filtered the database to Humira-only reports, then counted the top ten reactions within that subset.

**Key finding:** Injection site pain appears immediately — a reaction almost invisible in the all-drug view, but prominent here because Humira is self-injected. This is **confounding by route of administration**: the delivery method, not just the molecule, shapes the reaction profile. "Rheumatoid Arthritis" appearing as a reported reaction is **confounding by indication** — patients report their underlying condition worsening, which looks like a drug reaction in the data but may just be disease progression.

---

### 4. A drug's reports over time — `zantac_trend.py`
Fetched yearly report totals for Zantac (ranitidine) from 2013 to 2023, using date-range filtering to count one year at a time.

**Key finding:** Reports held steady at roughly 2,000–5,000 per year through 2018. After the FDA's NDMA contamination warning in 2019 and full market withdrawal in 2020, reports exploded — peaking at **151,982 in 2021**, sixty times the pre-recall baseline. The drug was already off shelves by then. The spike was driven by **mass-tort litigation**: law firms encouraged anyone who had ever taken Zantac to file reports. This is **notoriety bias** — the legal and media environment, not new clinical harm, caused the surge.

---

## The overarching takeaway

> **FAERS report counts measure attention — clinical, regulatory, media, and legal — far more than they measure harm.**

Every analysis ran into the same wall: the number of reports for a drug or reaction is shaped by who bothers to report, when they report, and why. Understanding that gap between signal and noise is the foundational skill in pharmacovigilance.

---

## Tools and files

| File | What it does |
|---|---|
| `explore.py` | Top 10 reactions, all drugs, all years |
| `top_drugs.py` | Top 10 most-reported drugs + bar chart |
| `humira_reactions.py` | Top 10 reactions for Humira + bar chart |
| `zantac_trend.py` | Zantac reports per year 2013–2023 + line chart |
| `top_drugs.png` | Bar chart: most-reported drugs |
| `humira_reactions.png` | Bar chart: Humira reaction profile |
| `zantac_trend.png` | Line chart: Zantac report trend with recall annotation |

**Stack:** Python 3 · pandas · matplotlib · requests · openFDA drug/event API (free, no key required)

---

## Limitations

- **Spontaneous and unverified:** FAERS reports are filed voluntarily — there is no confirmation that the drug actually caused the event.
- **No denominator:** report counts cannot be converted into rates because we don't know how many people took each drug.
- **Duplicate reports:** the same event is often filed separately by the patient, their doctor, and the manufacturer.
- **Counts are skewed by reporting and notoriety bias:** media coverage, litigation, and regulatory actions inflate report volumes independently of any change in clinical risk.
