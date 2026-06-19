# zantac_trend.py — Zantac (ranitidine) adverse-event reports per year in FAERS

import time
import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

# ── 1. Define what we're looking at ───────────────────────────────────────────

DRUG  = "ZANTAC"
YEARS = range(2013, 2024)   # 2013 → 2023 inclusive; covers pre/post recall

# ── 2. Fetch one total per year ───────────────────────────────────────────────
#
# New pattern: instead of one API call that counts categories, we make
# one call PER YEAR. Each call asks:
#   "How many ZANTAC reports were received in [year]?"
#
# The answer comes from response["meta"]["results"]["total"] — a single
# integer that the server calculated for us.
#
# URL breakdown:
#
#   search=patient.drug.medicinalproduct:"ZANTAC"
#       ↳ only reports that mention Zantac (same filter as last time)
#
#   +AND+
#       ↳ both conditions must be true (like AND in plain English)
#
#   receivedate:[20190101+TO+20191231]
#       ↳ only reports where the receive date falls inside this year
#         receivedate is formatted YYYYMMDD
#
#   &limit=1
#       ↳ we don't need actual report records — just the total count
#         in the metadata. Fetching 1 record keeps the response tiny.

print(f"Fetching yearly report counts for {DRUG} (2013–2023)...\n")

rows = []

for year in YEARS:
    start_date = f"{year}0101"   # e.g. "20190101"
    end_date   = f"{year}1231"   # e.g. "20191231"

    url = (
        "https://api.fda.gov/drug/event.json"
        f"?search=patient.drug.medicinalproduct:\"{DRUG}\""
        f"+AND+receivedate:[{start_date}+TO+{end_date}]"
        "&limit=1"
    )

    response = requests.get(url)

    # The API returns a 404 status code (not an error — just "no results")
    # when there are zero matching reports for a given year.
    # We catch that case and record 0 instead of crashing.
    if response.status_code == 404:
        print(f"  {year}: 0 reports")
        rows.append({"Year": year, "Reports": 0})
        time.sleep(0.25)
        continue

    response.raise_for_status()
    data     = response.json()
    total    = data["meta"]["results"]["total"]

    print(f"  {year}: {total:,} reports")
    rows.append({"Year": year, "Reports": total})

    # A short pause between calls is polite to the free public API —
    # it prevents us from accidentally sending too many requests too fast.
    time.sleep(0.25)

# ── 3. Build the DataFrame ────────────────────────────────────────────────────
#
# rows is now a list of dicts: [{"Year": 2013, "Reports": 412}, ...]
# pd.DataFrame() turns that into a two-column table.

df = pd.DataFrame(rows)

# ── 4. Print the table ────────────────────────────────────────────────────────

print(f"\nZANTAC Adverse-Event Reports per Year (FAERS)\n")
print(df.to_string(index=False))

# ── 5. Draw the line chart ────────────────────────────────────────────────────
#
# A line chart is the right choice for time-series data because the line
# visually implies continuity — one year flows into the next.
# Bar charts are better when the categories are independent (drug names,
# reaction terms). Years are not independent — they form a sequence.

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    df["Year"],
    df["Reports"],
    color="steelblue",
    linewidth=2.5,
    marker="o",        # a dot at each data point so individual years are clear
    markersize=7,
    markerfacecolor="white",
    markeredgewidth=2,
)

# ── 6. Annotate each data point with its count ───────────────────────────────
#
# For each (year, count) pair, we write the number just above the dot.
# va="bottom" means the text sits above the point.

for _, row in df.iterrows():
    ax.annotate(
        f"{int(row['Reports']):,}",
        xy=(row["Year"], row["Reports"]),
        xytext=(0, 10),           # shift the label 10 points upward
        textcoords="offset points",
        ha="center",
        fontsize=8,
        color="steelblue",
    )

# ── 7. Mark the recall event ─────────────────────────────────────────────────
#
# Context is everything in pharmacovigilance data.
# A vertical dashed line and annotation show WHY the spike happened.

ax.axvline(x=2019, color="crimson", linestyle="--", linewidth=1.5, alpha=0.7)
ax.text(
    2019.1, ax.get_ylim()[1] * 0.85,
    "FDA NDMA\nwarning (2019)",
    color="crimson",
    fontsize=9,
)

# ── 8. Style the chart ────────────────────────────────────────────────────────

ax.set_title(
    f"ZANTAC Adverse-Event Reports per Year\n(FAERS via openFDA)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("Number of Reports", fontsize=11)

# Force integer year labels on x-axis (no decimals like 2018.5)
ax.set_xticks(df["Year"])
ax.set_xticklabels(df["Year"], rotation=45, ha="right")

ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.yaxis.grid(True, linestyle="--", alpha=0.4)
ax.set_axisbelow(True)

plt.tight_layout()

# ── 9. Save ───────────────────────────────────────────────────────────────────

OUTPUT_FILE = "zantac_trend.png"
plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
print(f"\nChart saved as: {OUTPUT_FILE}")
