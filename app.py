# app.py — interactive FAERS dashboard powered by Streamlit
#
# Streamlit works by running this script from top to bottom every time the
# user interacts with the page (types in a box, clicks a button, etc.).
# Each st.* call below adds one visible element to the browser page.

import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from typing import Optional

# ── Page configuration ────────────────────────────────────────────────────────
# This must be the very first Streamlit call in the file.
# It sets the browser tab title and uses the full page width.

st.set_page_config(
    page_title="FAERS Explorer",
    page_icon="💊",
    layout="centered",
)

st.title("💊 FAERS Adverse Event Explorer")
st.markdown(
    "Search the FDA's public adverse-event database (FAERS) via the "
    "[openFDA API](https://open.fda.gov/apis/drug/event/). "
    "Pick any drug name to see its reaction profile and report history."
)

with st.expander("⚠️ How to read this data", expanded=True):
    st.markdown(
        "- **These are reports, not proven side effects.** A report only means someone "
        "suspected a link — there's no confirmation the drug caused the event.\n"
        "- **No denominator.** We don't know how many people took each drug, so counts "
        "can't be turned into actual risk rates.\n"
        "- **Reporting & notoriety bias.** Media coverage, recalls, and lawsuits inflate "
        "report counts independently of any real change in risk.\n"
        "- **Duplicates.** The same event is often filed separately by the patient, "
        "their doctor, and the manufacturer."
    )

# ── Drug name input ───────────────────────────────────────────────────────────
# st.text_input() renders a text box on the page.
# Whatever the user types is returned as a string and stored in `drug`.
# value= sets the default text that appears when the page first loads.

drug = st.text_input("Drug name (all caps works best, e.g. HUMIRA, OZEMPIC, ASPIRIN):",
                     value="HUMIRA").strip().upper()

if not drug:
    st.info("Type a drug name above and press Enter.")
    st.stop()   # st.stop() halts the rest of the script — nothing below renders

st.divider()

# ── Data-fetching functions ───────────────────────────────────────────────────
# @st.cache_data tells Streamlit to remember the result of a function call.
# The next time the same function is called with the same arguments (same drug
# name), Streamlit returns the saved result instantly instead of hitting the
# API again. This is what makes tab-switching and re-runs feel instant.

@st.cache_data(show_spinner=False)
def fetch_reactions(drug_name: str) -> Optional[pd.DataFrame]:
    """Return top-10 reactions for drug_name, or None if no reports found."""
    url = (
        "https://api.fda.gov/drug/event.json"
        f'?search=patient.drug.medicinalproduct:"{drug_name}"'
        "&count=patient.reaction.reactionmeddrapt.exact"
        "&limit=10"
    )
    resp = requests.get(url, timeout=10)
    if resp.status_code == 404:   # API returns 404 when zero results match
        return None
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["results"])
    df.columns = ["Reaction", "Reports"]
    return df


@st.cache_data(show_spinner=False)
def fetch_yearly_trend(drug_name: str, start: int = 2013, end: int = 2023) -> pd.DataFrame:
    """Return a year-by-year report count for drug_name (one API call per year)."""
    rows = []
    for year in range(start, end + 1):
        url = (
            "https://api.fda.gov/drug/event.json"
            f'?search=patient.drug.medicinalproduct:"{drug_name}"'
            f"+AND+receivedate:[{year}0101+TO+{year}1231]"
            "&limit=1"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            rows.append({"Year": year, "Reports": 0})
        else:
            resp.raise_for_status()
            rows.append({"Year": year, "Reports": resp.json()["meta"]["results"]["total"]})
        time.sleep(0.25)   # stay polite to the free public API
    return pd.DataFrame(rows)


# ── Tab layout ────────────────────────────────────────────────────────────────
# st.tabs() creates clickable tabs. The code inside each `with tab:` block
# only appears inside that tab — but Streamlit still *executes* all the code
# on every run; the cache (above) ensures that doesn't cause extra API calls.

tab1, tab2 = st.tabs(["📊 Top 10 Reactions", "📈 Reports per Year"])

# ── Tab 1: bar chart of top reactions ────────────────────────────────────────

with tab1:
    # st.spinner shows an animated "Loading…" message while the indented
    # code runs. It disappears automatically when the block finishes.
    with st.spinner(f"Fetching top reactions for {drug}…"):
        try:
            df_rx = fetch_reactions(drug)
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")
            st.stop()

    if df_rx is None:
        st.warning(
            f"No FAERS reports found for **{drug}**. "
            "Check the spelling or try a different brand/generic name."
        )
    else:
        st.subheader(f"Top 10 Adverse Reactions — {drug}")

        # Build a horizontal bar chart using matplotlib (same style as
        # humira_reactions.py, but now embedded in the browser via st.pyplot).
        df_sorted = df_rx.sort_values("Reports", ascending=True)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(df_sorted["Reaction"], df_sorted["Reports"],
                color="darkorange", edgecolor="white")

        # Count labels inside each bar
        for bar, count in zip(ax.patches, df_sorted["Reports"]):
            ax.text(
                bar.get_width() * 0.97,
                bar.get_y() + bar.get_height() / 2,
                f"{count:,}",
                va="center", ha="right",
                color="white", fontweight="bold", fontsize=9,
            )

        ax.set_xlabel("Number of Adverse Event Reports", fontsize=11)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.xaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)
        plt.tight_layout()

        # st.pyplot() renders the matplotlib figure inline in the browser.
        # clear_figure=True frees the memory after rendering.
        st.pyplot(fig, clear_figure=True)

        st.markdown("**Raw data**")
        # st.dataframe() renders an interactive, sortable table.
        st.dataframe(df_rx, use_container_width=True, hide_index=True)


# ── Tab 2: line chart of reports per year ────────────────────────────────────

with tab2:
    st.caption("Fetches one API call per year (2013–2023). "
               "First load takes ~10 seconds; subsequent loads are instant.")

    with st.spinner(f"Fetching yearly trend for {drug} — please wait…"):
        try:
            df_trend = fetch_yearly_trend(drug)
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")
            st.stop()

    if df_trend["Reports"].sum() == 0:
        st.warning(f"No yearly data found for **{drug}** in 2013–2023.")
    else:
        st.subheader(f"Reports per Year — {drug}")

        # Line chart — same logic as zantac_trend.py
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(
            df_trend["Year"], df_trend["Reports"],
            color="steelblue", linewidth=2.5,
            marker="o", markersize=7,
            markerfacecolor="white", markeredgewidth=2,
        )

        # Label each dot with its count
        for _, row in df_trend.iterrows():
            if row["Reports"] > 0:
                ax2.annotate(
                    f"{int(row['Reports']):,}",
                    xy=(row["Year"], row["Reports"]),
                    xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=8, color="steelblue",
                )

        ax2.set_xlabel("Year", fontsize=11)
        ax2.set_ylabel("Reports", fontsize=11)
        ax2.set_xticks(df_trend["Year"])
        ax2.set_xticklabels(df_trend["Year"], rotation=45, ha="right")
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{int(x):,}")
        )
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax2.set_axisbelow(True)
        plt.tight_layout()

        st.pyplot(fig2, clear_figure=True)

        st.markdown("**Raw data**")
        st.dataframe(df_trend, use_container_width=True, hide_index=True)
