import streamlit as st
import pandas as pd
from utils.mongoDB import load_electricity_data
import plotly.express as px


st.title("Electricity flows")

# Load data from MongoDB
data = load_electricity_data()
df = pd.DataFrame(data)

# Split the page into two columns
col1, col2 = st.columns(2, gap="large")

# possible connections 
connections = [
    ("NO_1", "SE_3"),
    ("NO_3", "SE_2"),
    ("NO_4", "SE_1"),
    ("NO_4", "SE_2"),
    ("NO_4", "FI"),
    ("NO_2", "DK_1"),
    ("NO_2", "NL"),
    ("NO_2", "DE_LU"),
    ("NO_2", "GB")
]

connection_options = []

for nor, neighbor in connections:
    connection_options.append((nor, neighbor))
    connection_options.append((neighbor, nor))

# left column 
with col1:
    st.subheader("Electricity imports and exports")

    selected_connection = st.radio(
        "Select connection:",
        options=connections,
        format_func=lambda x: f"{x[0]} ↔ {x[1]}"
    )

    year = st.selectbox(
        "Select year:",
        options=[2024, 2025, 2026]
    )

    norway, neighbor = selected_connection

    # Filter by selected connection (both directions) and year
    filtered_df = df[
        (
            ((df["from_zone"] == norway) & (df["to_zone"] == neighbor)) |
            ((df["from_zone"] == neighbor) & (df["to_zone"] == norway))
        ) &
        (df["timestamp"].dt.year == year)
    ].copy()

    # Aggregate by direction
    pie_data = (
        filtered_df.groupby("direction", as_index=False)["quantity_mw"]
        .sum()
    )

    # Plot pie chart
    fig = px.pie(
        pie_data,
        names="direction",
        values="quantity_mw",
        color="direction",
        color_discrete_map={
            "import": "#F48FB1",
            "export": "#74B9FF"
        },
        title=f"Pie chart of electricity flow: {norway} ↔ {neighbor} ({year})"
    )

    st.plotly_chart(fig, use_container_width=True)

# right column 
with col2:
    st.subheader("Electricity flow over time")

    # Select connection
    selected_connection_line = st.selectbox(
        "Select connection:",
        options=connections,
        format_func=lambda x: f"{x[0]} ↔ {x[1]}"
    )

    norway, neighbor = selected_connection_line

    # Select months
    months = list(range(1, 13))

    selected_months = st.pills(
        "Select months:",
        options=months,
        format_func=lambda x: pd.Timestamp(2025, x, 1).strftime("%B"),
        selection_mode="multi",
        default=[1]
    )

    # Filter by connection (both directions) and selected months
    filtered_line = df[
        (
            ((df["from_zone"] == norway) & (df["to_zone"] == neighbor)) |
            ((df["from_zone"] == neighbor) & (df["to_zone"] == norway))
        ) &
        (df["timestamp"].dt.month.isin(selected_months))
    ].copy()

    if filtered_line.empty:
        st.warning("No data available for the selected months.")
    else:
        # Create separate lines for import and export
        fig_line = px.line(
            filtered_line.sort_values("timestamp"),
            x="timestamp",
            y="quantity_mw",
            color="direction",
            color_discrete_map={
                "import": "#F48FB1",
                "export": "#74B9FF"
            },
            title=f"Electricity flow: {norway} ↔ {neighbor}",
            labels={
                "timestamp": "Date",
                "quantity_mw": "Electricity flow (MW)",
                "direction": "Direction"
            }
        )

        st.plotly_chart(fig_line, use_container_width=True)

# data source information 
with st.expander("About the data"):
    st.markdown("""
    The cross border electricity flow data were obtained from the ENTSO-E API (https://transparency.entsoe.eu/) and stored in MongoDB Atlas. The dataset includes electricity imports and exports between Norway and neighboring countries, measured in megawatts (Mw).
    """)