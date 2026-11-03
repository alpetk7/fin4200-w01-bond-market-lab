import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="FIN4200 Bond Market Explorer",
    page_icon="📈",
    layout="centered"
)

# ---------------------------------------------------
# LOAD BOND MARKET DATA
# ---------------------------------------------------

DATA_PATH = Path(__file__).parent / "temp" / "bond_data.csv"

@st.cache_data
def load_data(file_mtime):
    # file_mtime is only a cache key: the cache refreshes when the CSV changes
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False),
            errors="coerce"
        )

    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)
    return df.sort_values("Year").reset_index(drop=True)


if not DATA_PATH.exists():
    st.error("Missing data file: temp/bond_data.csv")
    st.stop()

df = load_data(DATA_PATH.stat().st_mtime)

MARKETS = [
    c for c in df.columns
    if c not in [
        "Year", "Total", "Estimated", "GDP",
        "Surplus/Deficit % GDP", "Recession Months"
    ]
]

# ---------------------------------------------------
# LIVE US DEBT DATA (US Treasury Fiscal Data API)
# ---------------------------------------------------

FISCAL_API = (
    "https://api.fiscaldata.treasury.gov/services/api/"
    "fiscal_service/v2/accounting/od/"
)

# Last known values, used only if the API cannot be reached
FALLBACK_DEBT = {
    "record_date": "2026-10-30",
    "total": 40524.5,          # $ billions
    "public": 32738.4,
    "intragov": 7786.1,
    "year_ago_total": None,
    "avg_rate": 3.518,         # %
    "avg_rate_date": "2026-09-30",
    "gdp_year_total": None,
    "live": False,
}


def fiscal_query(endpoint, **params):
    url = FISCAL_API + endpoint + "?" + urlencode(params)
    with urlopen(url, timeout=10) as response:
        return json.load(response)["data"]


def debt_on_or_before(day):
    """Latest Debt to the Penny record on or before a date."""
    return fiscal_query(
        "debt_to_penny",
        sort="-record_date",
        **{"page[size]": 1, "filter": f"record_date:lte:{day}"}
    )[0]


@st.cache_data(ttl=3600)
def load_live_debt(gdp_year):
    try:
        latest = debt_on_or_before(date.today().isoformat())
        latest_date = date.fromisoformat(latest["record_date"])
        year_ago = debt_on_or_before(
            (latest_date - timedelta(days=365)).isoformat()
        )
        gdp_year_end = debt_on_or_before(f"{gdp_year}-12-31")
        rate = fiscal_query(
            "avg_interest_rates",
            sort="-record_date",
            **{
                "page[size]": 1,
                "filter": "security_desc:eq:Total Marketable"
            }
        )[0]

        billions = lambda rec, key: float(rec[key]) / 1e9

        return {
            "record_date": latest["record_date"],
            "total": billions(latest, "tot_pub_debt_out_amt"),
            "public": billions(latest, "debt_held_public_amt"),
            "intragov": billions(latest, "intragov_hold_amt"),
            "year_ago_total": billions(year_ago, "tot_pub_debt_out_amt"),
            "avg_rate": float(rate["avg_interest_rate_amt"]),
            "avg_rate_date": rate["record_date"],
            "gdp_year_total": billions(gdp_year_end, "tot_pub_debt_out_amt"),
            "live": True,
        }
    except Exception:
        return FALLBACK_DEBT


live_debt = load_live_debt(int(df["Year"].max()))

# ---------------------------------------------------
# CASE DISCUSSION QUESTIONS
# ---------------------------------------------------

QUESTIONS = {
    "Q1: Early 2000s": {
        "years": (1996, 2004),
        "markets": ["Treasury"],
        "question": (
            "What happened to Treasury debt in the early 2000s? "
                    ),
        "followup": (
            "How did tax cuts, the dot-com recession, "
            "and government spending affect the US Government borrowing?"
        ),
    },

    "Q2: Financial Crisis 2007-2008": {
        "years": (1996, 2012),
        "markets": ["Treasury"],
        "question": (
            "What caused the large growth in the Treasury "
            "market starting in 2007/2008? "
        ),
        "followup": (
            "How did the recession, TARP, and the collapse "
            "of securitization markets affect these trends?"
        ),
        "background_title": "Background: TARP",
        "background": (
            "The **Troubled Asset Relief Program (TARP)** was created by "
            "the Emergency Economic Stabilization Act, signed October 3, "
            "2008, at the height of the financial crisis. Congress "
            "authorized up to $700 billion (later cut to about $475 "
            "billion) for the Treasury to stabilize the financial "
            "system. About $440 billion was actually disbursed, mainly to:\n\n"
            "- **Banks**, through preferred-stock purchases that "
            "injected capital (the Capital Purchase Program, about "
            "$205 billion)\n"
            "- **AIG**, the insurer that had sold credit protection on "
            "mortgage securities\n"
            "- **Automakers** GM and Chrysler and their finance arms\n"
            "- **Mortgage relief and credit markets**, including support "
            "for securitization of consumer and small-business loans\n\n"
            "TARP itself explains only a small part of the growth in "
            "Treasury debt, because most of the money was repaid with "
            "returns and the final cost was a few tens of billions of "
            "dollars. The larger drivers were the deep recession, which "
            "cut tax revenue, the 2009 fiscal stimulus (ARRA, about "
            "$800 billion), and the Federal Reserve's bond purchases "
            "alongside strong investor demand for safe assets. "
            "Compare the Treasury line with the Mortgage Related and "
            "Asset-Backed lines to see how private securitization "
            "shrank while government borrowing grew."
        ),
    },

    "Q3: Mortgage-Backed Securities": {
        "years": (2002, 2016),
        "markets": [
            "Agency MBS",
            "Non-Agency MBS"
        ],
        "question": (
            "What happened to mortgage-related securities "
            "before and after the subprime mortgage crisis?"
        ),
        "followup": (
            "Can aggregate mortgage-related securities data "
            "tell us what happened specifically to non-agency MBS?"
        ),
    },

    "Q4: COVID-19 and Treasury Debt": {
        "years": (2018, 2022),
        "markets": ["Treasury"],
        "question": (
            "How did the Treasury market change during COVID-19? "
            "Why did investors continue buying Treasuries?"
        ),
        "followup": (
            "Would government borrowing have been different "
            "if interest rates were 4-5% instead of near zero?"
        ),
        "background_title": "Background: the CARES Act",
        "background": (
            "The **Coronavirus Aid, Relief, and Economic Security "
            "(CARES) Act**, signed March 27, 2020, was the first and "
            "largest US pandemic relief package, at about $2.2 trillion. "
            "It funded:\n\n"
            "- **Direct payments** of $1,200 per adult and $500 per "
            "child for most households\n"
            "- **Expanded unemployment insurance**, including an extra "
            "$600 per week and coverage for gig workers\n"
            "- **Paycheck Protection Program** forgivable loans to small "
            "businesses that kept workers on payroll\n"
            "- **Loans and aid** for airlines, hospitals, and state and "
            "local governments\n\n"
            "The spending was financed by borrowing, not new taxes, so "
            "the Treasury sold much more debt (largely short-term "
            "T-bills). At the same time tax revenue fell in the "
            "recession, and the Federal Reserve cut rates to near zero "
            "and bought Treasuries."
        ),
    },

    "Explore All Years": {
        "years": (1980, 2024),
        "markets": [
            "Treasury",
            "Corporate Debt",
            "Mortgage Related"
        ],
        "question": (
            "How has the composition of the US bond market "
            "changed over time?"
        ),
        "followup": (
            "Which market segments grew most rapidly?"
        ),
    },
}

# ---------------------------------------------------
# CHART CONTEXT: RECESSIONS AND KEY EVENTS
# ---------------------------------------------------

def recession_spans(data, min_months=2):
    """Group years with NBER recession months (FRED USREC) into spans."""
    recession_years = data.loc[
        data["Recession Months"] >= min_months, "Year"
    ].tolist()

    spans = []
    for year in recession_years:
        if spans and year == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], year)
        else:
            spans.append((year, year))
    return spans


# Calendar years with at least 2 NBER recession months
RECESSIONS = recession_spans(df)

EVENTS = [
    (2001, "Tax cuts"),
    (2008, "TARP"),
    (2020, "CARES Act"),
]

# US sovereign credit rating downgrades (year, label)
DOWNGRADES = [
    (2011, "S&P: AAA to AA+"),
    (2023, "Fitch: AAA to AA+"),
    (2025, "Moody's: Aaa to Aa1"),
]

PROJECTION_YEARS = 10

Y_AXIS_TITLES = {
    "Outstanding Balances": "$ trillions",
    "Market Shares": "% of total market",
    "Indexed Growth": "Index (first year = 100)",
}

# ---------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------

st.title("📈 US Bond Market Explorer")

st.caption(
    "FIN4200 Applied Finance Lab | University of Denver "
    "Historical US bond markets, 1980-2024"
)

st.info(
    "This dataset measures securities outstanding "
    "in billions of dollars. Outstanding balances are "
    "not the same as annual issuance or trading volume."
)

tab0, tab1, tab2 = st.tabs([
    "🥧 Market Snapshot",
    "📊 Bond Market History",
    "🕒 National Debt Clock"
])

# ---------------------------------------------------
# TAB 0: MARKET SNAPSHOT
# ---------------------------------------------------

# Agency MBS and Non-Agency MBS are subsets of Mortgage Related,
# so only the non-overlapping segments are shown.
SEGMENTS = [m for m in MARKETS if m not in ["Agency MBS", "Non-Agency MBS"]]

with tab0:

    st.subheader("What Does the US Bond Market Look Like?")

    snapshot_year = st.slider(
        "Select Year",
        min_value=int(df["Year"].min()),
        max_value=int(df["Year"].max()),
        value=int(df["Year"].max()),
        key="snapshot_year"
    )

    row = df[df["Year"] == snapshot_year].iloc[0]

    pie_data = row[SEGMENTS].dropna()

    fig_pie = go.Figure(go.Pie(
        labels=pie_data.index,
        values=pie_data.values / 1000,
        hole=0.45,
        sort=False,
        textinfo="label+percent",
        hovertemplate="%{label}: $%{value:,.2f}T<extra></extra>"
    ))

    fig_pie.update_layout(
        height=450,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        annotations=[dict(
            text=f"<b>${row['Total'] / 1000:,.1f}T</b><br>{snapshot_year}",
            showarrow=False,
            font_size=18
        )]
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    st.caption(
        "Share of total US bond market securities outstanding. "
        "Drag the slider to see how the mix has changed."
    )

    g1, g2 = st.columns(2)

    g1.metric(
        f"Treasury debt, % of GDP ({snapshot_year})",
        f"{row['Treasury'] / row['GDP'] * 100:.0f}%"
    )

    g2.metric(
        f"Total bond market, % of GDP ({snapshot_year})",
        f"{row['Total'] / row['GDP'] * 100:.0f}%"
    )

# ---------------------------------------------------
# TAB 1: HISTORICAL DATA
# ---------------------------------------------------

with tab1:

    st.subheader("Explore Historical Bond Market Trends")

    selected_question = st.selectbox(
        "Select a case discussion question",
        list(QUESTIONS.keys())
    )

    case = QUESTIONS[selected_question]

    st.markdown("### Discussion Question")
    st.write(case["question"])

    min_year = int(df["Year"].min())
    max_year = int(df["Year"].max())

    default_years = (
        max(min_year, case["years"][0]),
        min(max_year, case["years"][1])
    )

    years = st.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=default_years,
        key=selected_question
    )

    filtered = df[
        df["Year"].between(years[0], years[1])
    ].copy()

    categories = st.multiselect(
        "Select Bond Market Categories",
        options=MARKETS + ["Total"],
        default=case["markets"],
        key="categories_" + selected_question
    )

    chart_type = st.radio(
        "Choose Chart",
        [
            "Outstanding Balances",
            "Market Shares",
            "Indexed Growth"
        ],
        horizontal=True
    )

    if categories:

        chart_data = filtered[["Year"]].copy()

        for category in categories:

            values = filtered[category]

            if chart_type == "Outstanding Balances":
                chart_data[category] = values / 1000

            elif chart_type == "Market Shares":
                chart_data[category] = (
                    values / filtered["Total"] * 100
                )

            else:
                first_valid = values.dropna()

                if not first_valid.empty:
                    base = first_valid.iloc[0]

                    if base != 0:
                        chart_data[category] = (
                            values / base * 100
                        )

        plotted = [
            c for c in categories
            if c in chart_data.columns
        ]

        if plotted:
            show_events = st.checkbox(
                "Show recessions and key events",
                value=True
            )

            fig = go.Figure()

            for category in plotted:
                fig.add_trace(go.Scatter(
                    x=chart_data["Year"],
                    y=chart_data[category],
                    name=category,
                    mode="lines",
                    hovertemplate="%{y:,.2f}"
                ))

            if show_events:
                for start_year, end_year in RECESSIONS:
                    if end_year >= years[0] and start_year <= years[1]:
                        fig.add_vrect(
                            x0=start_year - 0.5,
                            x1=end_year + 0.5,
                            fillcolor="gray",
                            opacity=0.15,
                            line_width=0
                        )

                for event_year, label in EVENTS:
                    if years[0] <= event_year <= years[1]:
                        fig.add_vline(
                            x=event_year,
                            line_dash="dot",
                            line_color="gray",
                            annotation_text=label,
                            annotation_position="top left"
                        )

            fig.update_layout(
                height=420,
                hovermode="x unified",
                xaxis_title="Year",
                yaxis_title=Y_AXIS_TITLES[chart_type],
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2
                ),
                margin=dict(l=10, r=10, t=30, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

            if show_events:
                st.caption(
                    "Gray bands: NBER recessions. "
                    "Dotted lines: key fiscal events."
                )
        else:
            st.warning("No valid data available.")

    else:
        st.warning("Please select at least one category.")

    # -----------------------------------------------
    # FEDERAL BUDGET DEFICIT
    # -----------------------------------------------

    show_deficit = st.checkbox(
        "Show federal budget deficit (% of GDP)",
        value=selected_question[:2] in ("Q1", "Q2", "Q4"),
        key="deficit_" + selected_question
    )

    if show_deficit:
        fig_def = go.Figure(go.Bar(
            x=filtered["Year"],
            y=filtered["Surplus/Deficit % GDP"],
            marker_color=[
                "#d62728" if v < 0 else "#2ca02c"
                for v in filtered["Surplus/Deficit % GDP"]
            ],
            hovertemplate="%{y:.1f}% of GDP<extra></extra>"
        ))

        fig_def.update_layout(
            height=260,
            xaxis_title="Year",
            yaxis_title="Surplus (+) / deficit (-), % of GDP",
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig_def, use_container_width=True)

        st.caption(
            "Federal budget balance by fiscal year (source: FRED, "
            "FYFSGDA188S). Deficits are what the Treasury finances "
            "by issuing new debt."
        )

    # -----------------------------------------------
    # PERIOD COMPARISON
    # -----------------------------------------------

    st.subheader("Analyze Market Growth")

    if not categories:
        st.info("Select categories above to see their growth.")

    for selected_market in categories:

        valid = filtered[
            ["Year", selected_market]
        ].dropna()

        st.markdown(f"**{selected_market}**")

        if len(valid) < 2:
            st.caption("Not enough data in the selected years.")
            continue

        start = valid.iloc[0]
        end = valid.iloc[-1]

        start_value = start[selected_market]
        end_value = end[selected_market]

        change = end_value - start_value

        growth = (
            change / start_value * 100
            if start_value != 0 else 0
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            f"{int(start['Year'])} Outstanding",
            f"${start_value / 1000:.2f}T"
        )

        c2.metric(
            f"{int(end['Year'])} Outstanding",
            f"${end_value / 1000:.2f}T"
        )

        c3.metric(
            "Growth",
            f"{growth:+.1f}%"
        )

    # -----------------------------------------------
    # STUDENT AI EDITING CHALLENGE
    # -----------------------------------------------

    # STUDENT TASK:
    # Ask your AI coding assistant to add a new metric
    # showing Treasury market share in the END year.
    #
    # Formula:
    # Treasury outstanding / Total outstanding
    #
    # Compare your result against the Excel workbook.
    #
    # ADD YOUR NEW CODE BELOW THIS COMMENT.

    # -----------------------------------------------

    if selected_question.startswith("Q3"):
        st.info(
            "Agency MBS and Non-Agency MBS split Mortgage Related "
            "(source: SIFMA). Values for 2022-2024 are estimates "
            "that hold the 2021 non-agency share constant, because "
            "SIFMA's outstanding database is under maintenance."
        )

    st.markdown("### Follow-up Discussion")
    st.write(case["followup"])

    if "background" in case:
        with st.expander(case["background_title"], expanded=True):
            st.markdown(case["background"])

    with st.expander("View Underlying Data"):
        st.dataframe(
            filtered,
            hide_index=True,
            use_container_width=True
        )

# ---------------------------------------------------
# TAB 2: NATIONAL DEBT CLOCK
# ---------------------------------------------------

with tab2:

    # -----------------------------------------------
    # TREASURY DEBT OVER TIME
    # -----------------------------------------------

    st.subheader("Treasury Debt Over Time")

    hist = df[["Year", "Treasury", "GDP"]].dropna().reset_index(drop=True)
    hist["Ratio"] = hist["Treasury"] / hist["GDP"] * 100
    first_year = int(hist["Year"].min())
    last_year = int(hist["Year"].max())

    debt_view = st.radio(
        "Show",
        ["Debt-to-GDP ratio", "Debt and GDP ($ trillions)"],
        horizontal=True,
        key="debt_view"
    )

    sel_year = st.slider(
        "Select year",
        min_value=first_year,
        max_value=last_year,
        value=last_year,
        key="debt_year"
    )

    fit_years = st.slider(
        "Years of history used for the linear trend",
        min_value=5, max_value=20, value=10,
        key="debt_fit_years"
    )

    # Simple linear extrapolation of debt and GDP separately
    fit = hist.tail(fit_years)
    proj_years = np.arange(last_year + 1, last_year + PROJECTION_YEARS + 1)

    debt_slope, debt_icpt = np.polyfit(fit["Year"], fit["Treasury"], 1)
    gdp_slope, gdp_icpt = np.polyfit(fit["Year"], fit["GDP"], 1)

    proj_debt = debt_slope * proj_years + debt_icpt
    proj_gdp = gdp_slope * proj_years + gdp_icpt
    proj_ratio = proj_debt / proj_gdp * 100

    # Join the dashed projection to the last actual point
    link_years = np.concatenate([[last_year], proj_years])

    def with_last(actual, projected):
        return np.concatenate([[actual], projected])

    last_row = hist.iloc[-1]
    sel_row = hist[hist["Year"] == sel_year].iloc[0]

    fig_t = go.Figure()

    if debt_view == "Debt-to-GDP ratio":
        fig_t.add_trace(go.Scatter(
            x=hist["Year"], y=hist["Ratio"],
            name="Treasury debt / GDP", mode="lines",
            line=dict(color="#1f77b4"),
            hovertemplate="%{y:.1f}%"
        ))
        fig_t.add_trace(go.Scatter(
            x=link_years, y=with_last(last_row["Ratio"], proj_ratio),
            name="Linear projection", mode="lines",
            line=dict(color="#1f77b4", dash="dash"),
            hovertemplate="%{y:.1f}%"
        ))
        fig_t.add_trace(go.Scatter(
            x=[sel_year], y=[sel_row["Ratio"]],
            name="Selected year", mode="markers",
            marker=dict(size=12, color="#d62728"),
            hovertemplate="%{y:.1f}%"
        ))
        y_title = "Treasury debt, % of GDP"
    else:
        fig_t.add_trace(go.Scatter(
            x=hist["Year"], y=hist["Treasury"] / 1000,
            name="Treasury debt", mode="lines",
            line=dict(color="#1f77b4"),
            hovertemplate="$%{y:.2f}T"
        ))
        fig_t.add_trace(go.Scatter(
            x=link_years,
            y=with_last(last_row["Treasury"], proj_debt) / 1000,
            name="Debt projection", mode="lines",
            line=dict(color="#1f77b4", dash="dash"),
            hovertemplate="$%{y:.2f}T"
        ))
        fig_t.add_trace(go.Scatter(
            x=hist["Year"], y=hist["GDP"] / 1000,
            name="GDP", mode="lines",
            line=dict(color="#2ca02c"),
            hovertemplate="$%{y:.2f}T"
        ))
        fig_t.add_trace(go.Scatter(
            x=link_years,
            y=with_last(last_row["GDP"], proj_gdp) / 1000,
            name="GDP projection", mode="lines",
            line=dict(color="#2ca02c", dash="dash"),
            hovertemplate="$%{y:.2f}T"
        ))
        y_title = "$ trillions"

    for dg_year, dg_label in DOWNGRADES:
        fig_t.add_vline(
            x=dg_year, line_dash="dot", line_color="crimson"
        )
        fig_t.add_annotation(
            x=dg_year, y=1, yref="paper",
            text=dg_label, textangle=-90,
            showarrow=False, xanchor="right", yanchor="top",
            font=dict(color="crimson", size=11)
        )

    fig_t.update_layout(
        height=420,
        hovermode="x unified",
        xaxis_title="Year",
        yaxis_title=y_title,
        legend=dict(orientation="h", yanchor="top", y=-0.2),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig_t, use_container_width=True)

    st.caption(
        "Solid: actual (SIFMA Treasury debt, BEA GDP). Dashed: "
        f"straight-line trend fitted to the last {fit_years} years and "
        f"extended {PROJECTION_YEARS} years. Red dotted lines: US "
        "credit rating downgrades."
    )

    prev_rows = hist[hist["Year"] == sel_year - 1]

    if prev_rows.empty:
        debt_delta = gdp_delta = None
    else:
        prev = prev_rows.iloc[0]
        debt_delta = f"{(sel_row['Treasury'] / prev['Treasury'] - 1) * 100:+.1f}% vs {sel_year - 1}"
        gdp_delta = f"{(sel_row['GDP'] / prev['GDP'] - 1) * 100:+.1f}% vs {sel_year - 1}"

    t1, t2, t3 = st.columns(3)

    t1.metric(f"Debt / GDP ({sel_year})", f"{sel_row['Ratio']:.0f}%")
    t2.metric(
        f"Treasury debt ({sel_year})",
        f"${sel_row['Treasury'] / 1000:,.1f}T",
        debt_delta, delta_color="off"
    )
    t3.metric(
        f"GDP ({sel_year})",
        f"${sel_row['GDP'] / 1000:,.1f}T",
        gdp_delta, delta_color="off"
    )

    p1, p2 = st.columns(2)

    end_year = last_year + PROJECTION_YEARS

    p1.metric(
        f"Projected debt ({end_year})",
        f"${proj_debt[-1] / 1000:,.1f}T"
    )
    p2.metric(
        f"Projected debt / GDP ({end_year})",
        f"{proj_ratio[-1]:.0f}%",
        f"{proj_ratio[-1] - last_row['Ratio']:+.0f} pts vs {last_year}",
        delta_color="off"
    )

    st.caption(
        "A straight line is a crude projection: debt tends to grow "
        "faster than a line because interest compounds, and it ignores "
        "policy changes, recessions and interest rates. Try different "
        "trend windows to see how sensitive the answer is."
    )

    with st.expander("Notes: US credit rating downgrades", expanded=True):
        st.markdown(
            "The US lost its top credit rating from all three major "
            "agencies, one at a time:\n\n"
            "- **2011: Standard & Poor's, AAA to AA+.** The first "
            "downgrade in US history, in August 2011 after a bitter "
            "debt-ceiling standoff. S&P cited political brinkmanship and "
            "the lack of a plan to stabilize debt.\n"
            "- **2023: Fitch, AAA to AA+.** August 2023, after another "
            "debt-ceiling episode, citing expected fiscal deterioration, "
            "rising debt and weaker governance.\n"
            "- **2025: Moody's, Aaa to Aa1.** May 2025, citing rising "
            "debt and interest costs and the failure of governments to "
            "agree on reducing deficits. After this, none of the three "
            "agencies rates the US at its top grade.\n\n"
            "**Think about it:** Treasury yields fell, not rose, after "
            "the 2011 downgrade, because investors rushed to Treasuries "
            "as a safe asset during a market sell-off. Why would "
            "investors buy the debt of a country that was just "
            "downgraded? What does a rating measure, and what keeps "
            "demand for Treasuries high (the dollar's reserve role, "
            "market depth, the Fed)?"
        )

    st.subheader("US National Debt Right Now")

    if live_debt["live"]:
        st.caption(
            f"Source: US Treasury, Debt to the Penny. "
            f"Latest record: {live_debt['record_date']}."
        )
    else:
        st.warning(
            "Could not reach the Treasury data service. Showing the "
            f"last known values from {live_debt['record_date']}."
        )

    debt_total = live_debt["total"]
    debt_public = live_debt["public"]
    debt_intragov = live_debt["intragov"]

    k1, k2, k3 = st.columns(3)

    k1.metric("Total public debt", f"${debt_total / 1000:,.2f}T")
    k2.metric("Held by the public", f"${debt_public / 1000:,.2f}T")
    k3.metric("Intragovernmental", f"${debt_intragov / 1000:,.2f}T")

    st.caption(
        "Intragovernmental debt is owed to government accounts such as "
        "the Social Security trust funds. The bond market data in the "
        "other tabs counts marketable debt held by the public only."
    )

    latest_year = int(df["Year"].max())
    latest_gdp = df.loc[df["Year"] == latest_year, "GDP"].iloc[0]

    if live_debt["gdp_year_total"]:
        k4, k5 = st.columns(2)

        k4.metric(
            f"Total debt / GDP ({latest_year})",
            f"{live_debt['gdp_year_total'] / latest_gdp * 100:.0f}%"
        )

        k5.metric(
            "Est. annual interest on marketable debt",
            f"${debt_public * live_debt['avg_rate'] / 100:,.0f}B"
        )

        st.caption(
            f"Debt/GDP uses year-end {latest_year} debt and GDP so the "
            "dates match. Estimated interest = debt held by the public "
            f"x {live_debt['avg_rate']:.2f}% average rate on marketable "
            f"debt ({live_debt['avg_rate_date']}); it is a rough guide, "
            "not the Treasury's reported interest expense."
        )

    if live_debt["year_ago_total"]:
        per_year = debt_total - live_debt["year_ago_total"]
        per_second = per_year * 1e9 / (365 * 24 * 3600)

        s1, s2 = st.columns(2)

        s1.metric("Added over the past year", f"${per_year / 1000:,.2f}T")
        s2.metric("Added per second (avg.)", f"${per_second:,.0f}")

    st.markdown("### Discuss")

    st.write(
        "Why is total debt so much larger than the Treasury market in "
        "the other tabs? Why can the debt grow every second even in a "
        "year with a budget deficit that is shrinking?"
    )

    st.caption(
        "Debt clocks you see online estimate the total by extending "
        "this official daily series forward at its recent growth rate."
    )


st.caption(
    "FIN4200 Applied Finance Lab | "
    "University of Denver"
)
