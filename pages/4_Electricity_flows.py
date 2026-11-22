
import streamlit as st
import pandas as pd
from utils.mongoDB import load_electricity_data
import plotly.express as px
from utils.plotting import apply_plot_theme


st.title("Electricity flows")

FLOW_COLORS = {
    "import": "#1676C1",
    "export": "#D39A35"
}

# Load data from MongoDB
try:
    data = load_electricity_data()
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

df = pd.DataFrame(data)

# Ensure timestamps are datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Split the page into two columns
col1, col2 = st.columns(2, gap="large")

# Possible connections
connections = [
    ("NO_1", "SE_3"),
    ("NO_3", "SE_2"),
    ("NO_4", "SE_1"),
    ("NO_4", "SE_2"),
    ("NO_4", "FI"),
    ("NO_2", "DK_1"),
    ("NO_2", "NL"),
    ("NO_2", "DE_LU"),
    ("NO_2", "GB"),
]

# Available years in dataset
available_years = sorted(
    df["timestamp"].dt.year.dropna().unique().tolist(),
    reverse=True,
)

if not available_years:
    st.warning("No electricity flow data available.")
    st.stop()


# LEFT COLUMN - PIE CHART
with col1:
    st.subheader("Electricity imports and exports")

    selected_connection = st.radio(
        "Select connection:",
        options=connections,
        format_func=lambda x: f"{x[0]} ↔ {x[1]}",
    )

    year = st.selectbox(
        "Select year:",
        options=available_years,
        key="pie_year",
    )

    norway, neighbor = selected_connection

    # Filter by connection and year
    filtered_df = df[
        (
            (
                (df["from_zone"] == norway)
                & (df["to_zone"] == neighbor)
            )
            |
            (
                (df["from_zone"] == neighbor)
                & (df["to_zone"] == norway)
            )
        )
        & (df["timestamp"].dt.year == year)
    ].copy()

    if filtered_df.empty:
        st.warning("No data available for the selected year.")
    else:
        # Aggregate by direction
        pie_data = (
            filtered_df.groupby("direction", as_index=False)[
                "quantity_mw"
            ].sum()
        )

        # Plot pie chart
        fig = px.pie(
            pie_data,
            names="direction",
            values="quantity_mw",
            color="direction",
            color_discrete_map=FLOW_COLORS,
            title=(
                f"Pie chart of electricity flow: "
                f"{norway} ↔ {neighbor} ({year})"
            ),
        )

        fig = apply_plot_theme(fig)
        fig.update_traces(hovertemplate="%{label}: %{value:,.0f} MW (sum of records)<extra></extra>")

        st.plotly_chart(fig, use_container_width=True)


# RIGHT COLUMN - LINE CHART
with col2:
    st.subheader("Electricity flow over time")

    selected_connection_line = st.selectbox(
        "Select connection:",
        options=connections,
        format_func=lambda x: f"{x[0]} ↔ {x[1]}"
    )

    norway, neighbor = selected_connection_line

    # Select year
    line_year = st.selectbox(
        "Select year:",
        options=[2024, 2025, 2026],
        key="line_year"
    )

    # Select months
    months = list(range(1, 13))

    selected_months = st.pills(
        "Select months:",
        options=months,
        format_func=lambda x: pd.Timestamp(
            2025, x, 1
        ).strftime("%B"),
        selection_mode="multi",
        default=[1, 2, 3]
    )

    # Filter by connection, year and selected months
    filtered_line = df[
        (
            ((df["from_zone"] == norway) &
             (df["to_zone"] == neighbor)) |
            ((df["from_zone"] == neighbor) &
             (df["to_zone"] == norway))
        )
        & (df["timestamp"].dt.year == line_year)
        & (df["timestamp"].dt.month.isin(selected_months))
    ].copy()

    if filtered_line.empty:
        st.warning(
            "No data available for the selected period."
        )
    else:
        filtered_line = filtered_line.sort_values(
            ["direction", "timestamp"]
        )

        # Break lines when observations are more than
        # 2 hours apart (assuming hourly observations)
        def break_time_gaps(group):
            group = group.sort_values("timestamp").copy()

            gaps = group["timestamp"].diff()
            gap_starts = group.loc[
                gaps > pd.Timedelta(hours=2)
            ]

            if not gap_starts.empty:
                missing_rows = gap_starts.copy()
                missing_rows["timestamp"] = (
                    missing_rows["timestamp"]
                    - pd.Timedelta(nanoseconds=1)
                )
                missing_rows["quantity_mw"] = float("nan")

                group = pd.concat(
                    [group, missing_rows],
                    ignore_index=True
                ).sort_values("timestamp")

            return group

        filtered_line = pd.concat(
            [
                break_time_gaps(group)
                for _, group in filtered_line.groupby("direction")
            ],
            ignore_index=True
        )


        # Create line chart
        fig_line = px.line(
            filtered_line,
            x="timestamp",
            y="quantity_mw",
            color="direction",
            color_discrete_map=FLOW_COLORS,
            category_orders={
                "direction": ["import", "export"]
            },
            title=f"Electricity flow: {norway} ↔ {neighbor}",
            labels={
                "timestamp": "Date",
                "quantity_mw": "Electricity flow (MW)",
                "direction": "Direction"
            }
        )

        # Import: thinner and semi-transparent
        fig_line.update_traces(
            line=dict(width=1.5),
            opacity=0.55,
            connectgaps=False,
            selector=dict(name="import")
        )

        # Export: thicker and fully visible
        fig_line.update_traces(
            line=dict(width=2.5),
            opacity=1,
            connectgaps=False,
            selector=dict(name="export")
        )

        fig_line = apply_plot_theme(fig_line)

        st.plotly_chart(
            fig_line,
            use_container_width=True
        )


with st.expander('About the data'):
    st.markdown('Cross-border electricity data come from [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) and are retrieved from MongoDB. The underlying quantity is expressed in MW. The pie chart sums recorded MW values by direction; it does not directly represent total energy in MWh.')
