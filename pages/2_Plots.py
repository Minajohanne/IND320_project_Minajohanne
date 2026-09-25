import pandas as pd 
import streamlit as st 
import plotly.express as px 

st.title("Reservoir data plot")

@st.cache_data
def load_data(file):
    """Read reservoir data from the local CSV file."""
    return pd.read_csv(file)

# reading the data 
dat = load_data("data/reservoirs.csv") 

# converting "dato_Id" to a datetime object 
dat["dato_Id"] = pd.to_datetime(dat["dato_Id"]) 
dat = dat.sort_values("dato_Id")

# create year-month values for the select_slider
dat["month"] = dat["dato_Id"].dt.to_period("M").astype(str)
print(dat["month"])

# columns to choose from in the selectbox 
csv_cols = [col for col in dat.columns if col != "month"]
options = ["All columns"] + csv_cols

selected_column = st.selectbox(
    "select a variable",
    options 
) # columns that the used choose 

# month selecetion for the select_slider
months = dat["month"].unique().tolist()

# select_slider
selected_months = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])
)

# month range 
start_month, end_month = selected_months
filtered_dat = dat[
    (dat["month"] >= start_month) &
    (dat["month"] <= end_month)
]

# Plot all measurement columns
if selected_column == "All columns":
    plot_columns = [
        "fyllingsgrad",
        "kapasitet_TWh",
        "fylling_TWh",
        "fyllingsgrad_forrige_uke",
        "endring_fyllingsgrad",
    ]

    # There are multiple observations for each date.
    # Calculate the mean to get one value per date for each measurement.
    plot_data = (
        filtered_dat
        .groupby("dato_Id")[plot_columns]
        .mean()
        .reset_index()
    )

    # Make a copy so plot_data is not changed
    scaled_dat = plot_data.copy()

    # Min-max scaling of each measurement
    for col in plot_columns:
        col_min = scaled_dat[col].min()
        col_max = scaled_dat[col].max()

        scaled_dat[col] = (
            (scaled_dat[col] - col_min) /
            (col_max - col_min)
        )

    # Plot the scaled measurements together
    fig = px.line(
        scaled_dat,
        x="dato_Id",
        y=plot_columns,
        title="Scaled reservoir measurements over time",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Scaled value",
        legend_title="Variable",
        template="plotly_white",
    )

else:
    # Plot the selected column without averaging across areas
    fig = px.line(
        filtered_dat,
        x="dato_Id",
        y=selected_column,
        color="area_number",
        title=f"{selected_column} over time",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_column,
        template="plotly_white",
    )


st.plotly_chart(fig, width="stretch")