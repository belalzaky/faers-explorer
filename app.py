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
def fetch_demographics(drug_name: str) -> dict:
    """Return sex-split and age-group DataFrames for drug_name."""
    sex_labels  = {"1": "Male", "2": "Female", "0": "Unknown"}
    age_labels  = {"1": "Neonate", "2": "Infant", "3": "Child",
                   "4": "Adolescent", "5": "Adult", "6": "Elderly"}
    age_order   = ["Neonate", "Infant", "Child", "Adolescent", "Adult", "Elderly"]

    def _fetch_count(field: str) -> Optional[pd.DataFrame]:
        url = (
            "https://api.fda.gov/drug/event.json"
            f'?search=patient.drug.medicinalproduct:"{drug_name}"'
            f"&count={field}&limit=10"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return pd.DataFrame(resp.json()["results"])

    raw_sex = _fetch_count("patient.patientsex")
    if raw_sex is not None:
        raw_sex.columns = ["code", "Reports"]
        raw_sex["Sex"] = raw_sex["code"].astype(str).map(sex_labels).fillna("Unknown")
        df_sex = raw_sex[["Sex", "Reports"]]
    else:
        df_sex = None

    raw_age = _fetch_count("patient.patientagegroup")
    if raw_age is not None:
        raw_age.columns = ["code", "Reports"]
        raw_age["Age Group"] = raw_age["code"].astype(str).map(age_labels).fillna("Unknown")
        raw_age = raw_age[["Age Group", "Reports"]]
        # enforce the fixed age order for any groups that appear in the data
        raw_age["Age Group"] = pd.Categorical(
            raw_age["Age Group"], categories=age_order, ordered=True
        )
        df_age = raw_age.sort_values("Age Group").reset_index(drop=True)
    else:
        df_age = None

    return {"sex": df_sex, "age": df_age}


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

tab1, tab2, tab3, tab4 = st.tabs(["📊 Top 10 Reactions", "📈 Reports per Year", "👥 Demographics", "⚖️ Compare two drugs"])

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


# ── Tab 3: demographics (sex split + age groups) ─────────────────────────────

with tab3:
    with st.spinner(f"Fetching demographics for {drug}…"):
        try:
            demo = fetch_demographics(drug)
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")
            st.stop()

    df_sex = demo["sex"]
    df_age = demo["age"]

    if df_sex is None and df_age is None:
        st.warning(f"No demographic data found for **{drug}**.")
    else:
        st.subheader(f"Demographics — {drug}")
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Sex split**")
            if df_sex is None:
                st.info("No sex data available.")
            else:
                fig_s, ax_s = plt.subplots(figsize=(4, 3))
                ax_s.bar(df_sex["Sex"], df_sex["Reports"],
                         color="steelblue", edgecolor="white")
                ax_s.set_ylabel("Reports", fontsize=10)
                ax_s.yaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, _: f"{int(x):,}")
                )
                ax_s.spines["top"].set_visible(False)
                ax_s.spines["right"].set_visible(False)
                ax_s.yaxis.grid(True, linestyle="--", alpha=0.4)
                ax_s.set_axisbelow(True)
                plt.tight_layout()
                st.pyplot(fig_s, clear_figure=True)

        with col_right:
            st.markdown("**Age groups**")
            if df_age is None:
                st.info("No age data available.")
            else:
                fig_a, ax_a = plt.subplots(figsize=(4, 3))
                ax_a.bar(df_age["Age Group"], df_age["Reports"],
                         color="darkorange", edgecolor="white")
                ax_a.set_ylabel("Reports", fontsize=10)
                ax_a.tick_params(axis="x", rotation=30)
                ax_a.yaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, _: f"{int(x):,}")
                )
                ax_a.spines["top"].set_visible(False)
                ax_a.spines["right"].set_visible(False)
                ax_a.yaxis.grid(True, linestyle="--", alpha=0.4)
                ax_a.set_axisbelow(True)
                plt.tight_layout()
                st.pyplot(fig_a, clear_figure=True)

        st.markdown(
            "_Demographics only reflect reports that included these fields — "
            "many are left blank, so this is a partial picture._"
        )


# ── Tab 4: compare two drugs ──────────────────────────────────────────────────

with tab4:
    st.subheader("Compare top-10 reactions for two drugs")

    cmp_col1, cmp_col2 = st.columns(2)
    with cmp_col1:
        drug_a = st.text_input("Drug A:", value="HUMIRA", key="cmp_a").strip().upper()
    with cmp_col2:
        drug_b = st.text_input("Drug B:", value="ENBREL", key="cmp_b").strip().upper()

    if not drug_a or not drug_b:
        st.info("Enter both drug names above.")
    else:
        with st.spinner(f"Fetching reactions for {drug_a} and {drug_b}…"):
            try:
                df_a = fetch_reactions(drug_a)
                df_b = fetch_reactions(drug_b)
            except requests.RequestException as e:
                st.error(f"API request failed: {e}")
                st.stop()

        chart_col1, chart_col2 = st.columns(2)

        def _reaction_bar(ax, df, title):
            df_s = df.sort_values("Reports", ascending=True)
            ax.barh(df_s["Reaction"], df_s["Reports"],
                    color="darkorange", edgecolor="white")
            for bar, count in zip(ax.patches, df_s["Reports"]):
                ax.text(
                    bar.get_width() * 0.97,
                    bar.get_y() + bar.get_height() / 2,
                    f"{count:,}",
                    va="center", ha="right",
                    color="white", fontweight="bold", fontsize=7,
                )
            ax.set_title(title, fontsize=10, fontweight="bold")
            ax.set_xlabel("Reports", fontsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.xaxis.grid(True, linestyle="--", alpha=0.5)
            ax.set_axisbelow(True)

        with chart_col1:
            if df_a is None:
                st.warning(f"No data for **{drug_a}**.")
            else:
                fig_a, ax_a = plt.subplots(figsize=(4.5, 5))
                _reaction_bar(ax_a, df_a, drug_a)
                plt.tight_layout()
                st.pyplot(fig_a, clear_figure=True)

        with chart_col2:
            if df_b is None:
                st.warning(f"No data for **{drug_b}**.")
            else:
                fig_b, ax_b = plt.subplots(figsize=(4.5, 5))
                _reaction_bar(ax_b, df_b, drug_b)
                plt.tight_layout()
                st.pyplot(fig_b, clear_figure=True)

        # Overlap table — only shown when both fetches succeeded
        if df_a is not None and df_b is not None:
            shared = set(df_a["Reaction"]) & set(df_b["Reaction"])
            if shared:
                st.markdown("**Reactions in both top 10s**")
                overlap = (
                    df_a[df_a["Reaction"].isin(shared)]
                    .rename(columns={"Reports": f"Reports ({drug_a})"})
                    .merge(
                        df_b[df_b["Reaction"].isin(shared)]
                        .rename(columns={"Reports": f"Reports ({drug_b})"}),
                        on="Reaction",
                    )
                    .sort_values(f"Reports ({drug_a})", ascending=False)
                    .reset_index(drop=True)
                )
                st.dataframe(overlap, use_container_width=True, hide_index=True)
            else:
                st.info("No reactions appear in both top 10s.")
