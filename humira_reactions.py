# humira_reactions.py — top 10 adverse reactions reported for Humira in FAERS

import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # save to file without opening a window

# ── 1. Build the filtered API URL ─────────────────────────────────────────────
#
# The key new idea: the "search" parameter acts as a filter.
# Before counting anything, the API first narrows the dataset down to
# only the reports that mention a specific drug.
#
# URL breakdown:
#
#   search=patient.drug.medicinalproduct:"HUMIRA"
#       ↳ path to the drug-name field inside each report
#       ↳ "HUMIRA" is the value we're filtering for (exact string match)
#
#   &count=patient.reaction.reactionmeddrapt.exact
#       ↳ once filtered, count occurrences of each reaction term
#
#   &limit=10
#       ↳ return only the top 10 results
#
# Compare to our earlier scripts, which had no "search=" at all — those
# counted across ALL reports in the entire database, unfiltered.

DRUG = "HUMIRA"

URL = (
    "https://api.fda.gov/drug/event.json"
    f"?search=patient.drug.medicinalproduct:\"{DRUG}\""
    "&count=patient.reaction.reactionmeddrapt.exact"
    "&limit=10"
)

print(f"Fetching top 10 reactions for {DRUG} from openFDA...")
response = requests.get(URL)
response.raise_for_status()
data = response.json()

# ── 2. Build the DataFrame ────────────────────────────────────────────────────
#
# Same pattern as before: data["results"] is a list of {"term": ..., "count": ...}
# dicts. pd.DataFrame() turns that list into a table.

df = pd.DataFrame(data["results"])
df.columns = ["Reaction", "Number of Reports"]
df.insert(0, "Rank", range(1, len(df) + 1))

# ── 3. Print the table ────────────────────────────────────────────────────────

print(f"\nTop 10 Adverse Reactions Reported for {DRUG} in FAERS\n")
print(df.to_string(index=False))

# ── 4. Build the bar chart ────────────────────────────────────────────────────

df_chart = df.sort_values("Number of Reports", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))

ax.barh(
    df_chart["Reaction"],
    df_chart["Number of Reports"],
    color="darkorange",      # distinct colour from the previous drug chart
    edgecolor="white",
)

# Count labels inside each bar
for bar, count in zip(ax.patches, df_chart["Number of Reports"]):
    ax.text(
        bar.get_width() - bar.get_width() * 0.02,
        bar.get_y() + bar.get_height() / 2,
        f"{count:,}",
        va="center",
        ha="right",
        color="white",
        fontweight="bold",
        fontsize=9,
    )

# ── 5. Style the chart ────────────────────────────────────────────────────────

ax.set_title(
    f"Top 10 Adverse Reactions Reported for {DRUG}\n(openFDA FAERS data)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
ax.set_xlabel("Number of Adverse Event Reports", fontsize=11)
ax.set_ylabel("Reaction", fontsize=11)

ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.xaxis.grid(True, linestyle="--", alpha=0.5)
ax.set_axisbelow(True)

plt.tight_layout()

# ── 6. Save the chart ─────────────────────────────────────────────────────────

OUTPUT_FILE = f"{DRUG.lower()}_reactions.png"
plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
print(f"\nChart saved as: {OUTPUT_FILE}")
