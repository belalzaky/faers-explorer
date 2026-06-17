# top_drugs.py — top 10 most-reported drugs in FAERS, with a bar chart

import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt  # pyplot is the part of matplotlib we use to draw charts

# Use the non-interactive "Agg" backend so matplotlib saves files without
# trying to open a display window (important when running from a terminal).
matplotlib.use("Agg")

# ── 1. Fetch data from the openFDA API ───────────────────────────────────────
#
# We're counting by "medicinalproduct" — the drug name as submitted by the
# reporter. "exact" means treat the whole name as one value, not word-by-word.

URL = (
    "https://api.fda.gov/drug/event.json"
    "?count=patient.drug.medicinalproduct.exact"
    "&limit=10"
)

print("Fetching top 10 most-reported drugs from openFDA...")
response = requests.get(URL)
response.raise_for_status()
data = response.json()

# ── 2. Build a DataFrame ─────────────────────────────────────────────────────
#
# data["results"] is a list of dicts like: [{"term": "ASPIRIN", "count": 123}, ...]
# pd.DataFrame() turns that list into a two-column table.

df = pd.DataFrame(data["results"])
df.columns = ["Drug", "Number of Reports"]

# Rank from 1 (most reported) to 10
df.insert(0, "Rank", range(1, len(df) + 1))

# ── 3. Print the table ────────────────────────────────────────────────────────

print("\nTop 10 Most-Reported Drugs in FAERS\n")
print(df.to_string(index=False))

# ── 4. Build the bar chart ───────────────────────────────────────────────────
#
# We flip the DataFrame so rank 1 appears at the TOP of the chart.
# (matplotlib draws bars bottom-to-top, so the last row ends up on top.)

df_chart = df.sort_values("Number of Reports", ascending=True)

# figsize=(width, height) in inches — 10×6 gives plenty of room for labels
fig, ax = plt.subplots(figsize=(10, 6))

# barh() = horizontal bar chart
# y-axis = drug names  |  x-axis = report counts
ax.barh(
    df_chart["Drug"],            # bar labels (y-axis)
    df_chart["Number of Reports"],  # bar lengths (x-axis)
    color="steelblue",           # a clear, professional blue
    edgecolor="white",           # thin white line between bars
)

# ── 5. Add labels inside each bar ────────────────────────────────────────────
#
# For each bar we calculate the count and write it as text near the right end.
# This makes the chart readable without needing to squint at the x-axis.

for bar, count in zip(ax.patches, df_chart["Number of Reports"]):
    ax.text(
        bar.get_width() - bar.get_width() * 0.02,  # just inside the right edge
        bar.get_y() + bar.get_height() / 2,         # vertically centred on the bar
        f"{count:,}",           # formatted with commas, e.g. "1,234,567"
        va="center",            # vertical alignment
        ha="right",             # horizontal alignment
        color="white",
        fontweight="bold",
        fontsize=9,
    )

# ── 6. Style the chart ────────────────────────────────────────────────────────

ax.set_title(
    "Top 10 Most-Reported Drugs in FAERS\n(openFDA drug/event endpoint)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
ax.set_xlabel("Number of Adverse Event Reports", fontsize=11)
ax.set_ylabel("Drug Name", fontsize=11)

# Format x-axis numbers with commas (1000000 → 1,000,000)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

# Remove the top and right border lines — cleaner look
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Add subtle vertical grid lines so it's easy to read bar lengths
ax.xaxis.grid(True, linestyle="--", alpha=0.5)
ax.set_axisbelow(True)  # grid lines behind bars, not in front

plt.tight_layout()  # auto-adjust spacing so nothing gets clipped

# ── 7. Save the chart ─────────────────────────────────────────────────────────
#
# dpi=150 means 150 dots-per-inch — sharp enough to look crisp on screen
# and in documents without being an enormous file.

OUTPUT_FILE = "top_drugs.png"
plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
print(f"\nChart saved as: {OUTPUT_FILE}")
