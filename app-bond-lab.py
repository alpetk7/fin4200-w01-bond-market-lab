from pathlib import Path
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
def load_data():
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

df = load_data()

MARKETS = [
    c for c in df.columns
    if c not in ["Year", "Total", "Estimated"]
]

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
        "markets": ["Treasury", "Total"],
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

# NBER recession years (annual data, so shaded by calendar year)
RECESSIONS = [
    (1980, 1980), (1981, 1982), (1990, 1991),
    (2001, 2001), (2008, 2009), (2020, 2020),
]

EVENTS = [
    (2001, "Tax cuts"),
    (2008, "TARP"),
    (2020, "CARES Act"),
]

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
    "FIN4200 | Applied Finance Lab | "
    "Historical US bond markets, 1980-2024"
)

st.info(
    "This dataset measures securities outstanding "
    "in billions of dollars. Outstanding balances are "
    "not the same as annual issuance or trading volume."
)

tab1, tab2 = st.tabs([
    "📊 Bond Market History",
    "💵 Interest Rate Simulator"
])

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
# TAB 2: INTEREST RATE SCENARIO
# ---------------------------------------------------

with tab2:

    st.subheader(
        "What If Treasury Borrowing Costs "
        "Had Been Higher in 2020?"
    )

    st.write(
        "Explore how hypothetical Treasury borrowing "
        "costs change when interest rates increase."
    )

    borrowing = st.slider(
        "New Treasury Borrowing ($ billions)",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100
    )

    rate_low = st.slider(
        "Low Interest Rate (%)",
        0.0, 5.0, 0.5, 0.25
    )

    rate_high = st.slider(
        "High Interest Rate (%)",
        1.0, 10.0, 4.5, 0.25
    )

    interest_low = borrowing * rate_low / 100
    interest_high = borrowing * rate_high / 100

    difference = interest_high - interest_low

    a, b, c = st.columns(3)

    a.metric(
        "Annual Interest: Low Rate",
        f"${interest_low:,.1f}B"
    )

    b.metric(
        "Annual Interest: High Rate",
        f"${interest_high:,.1f}B"
    )

    c.metric(
        "Difference",
        f"${difference:+,.1f}B"
    )

    comparison = pd.DataFrame({
        "Scenario": [
            "Low Rate",
            "High Rate"
        ],
        "Interest Expense ($ billions)": [
            interest_low,
            interest_high
        ]
    })

    st.bar_chart(
        comparison.set_index("Scenario")
    )

    st.markdown("### Discussion")

    st.write(
        "Would Treasury issuance have been different "
        "if interest rates were 4-5% instead of near zero?"
    )

    st.write(
        "Consider fiscal constraints, interest expense, "
        "crowding out, and investor demand for safe assets."
    )

    st.caption(
        "Illustrative calculation for newly issued "
        "fixed-rate debt held for one year. "
        "Existing Treasury debt does not immediately "
        "reprice when market interest rates change."
    )


st.caption(
    "FIN4200 Applied Finance Lab | "
    "University of Denver"
)
