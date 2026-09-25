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

if selected_column == "All columns":
    # Only numerical measurement columns are meaningful together
    plot_columns = [
        "fyllingsgrad",
        "kapasitet_TWh",
        "fylling_TWh",
        "fyllingsgrad_forrige_uke",
        "endring_fyllingsgrad",
    ]

    fig = px.line(
        filtered_dat,
        x="dato_Id",
        y=plot_columns,
        title="Reservoir measurements over time",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Value",
        legend_title="Variable",
        template="plotly_white",
    )

else:
    fig = px.line(
        filtered_dat,
        x="dato_Id",
        y=selected_column,
        title=f"{selected_column} over time",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_column,
        template="plotly_white",
    )

st.plotly_chart(fig, width="stretch")

# endre navn på variabler? kan man bruke det som er gjort i notebooken?
# hvordan plotte kategoriske variabler? 
# del 1 av innleveringen - calculator - skal jeg fjerne den? 