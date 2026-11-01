from pathlib import Path
import pandas as pd
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
            st.line_chart(
                chart_data.set_index("Year")[plotted],
                height=400,
                use_container_width=True
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
