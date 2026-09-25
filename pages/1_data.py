import pandas as pd 
import streamlit as st 

st.title("Reservoir data table")

@st.cache_data
def load_data(file):
    """Read reservoir data from the local CSV file."""
    return pd.read_csv(file)

 # reading the data 
dat = load_data("data/reservoirs.csv")

# converting "dato_Id" to a datetime object 
dat["dato_Id"] = pd.to_datetime(dat["dato_Id"]) 
dat = dat.sort_values("dato_Id")

# find the first month of data 
first_date = dat["dato_Id"].min() 

first_month = dat[
    (dat["dato_Id"].dt.year == first_date.year) &
    (dat["dato_Id"].dt.month == first_date.month)
] 

# Display all observations from the first month
st.subheader("Data from the first month")

st.dataframe(
    first_month,
    hide_index=True,
    width="stretch"
)

# Variables for which a line chart is meaningful
plot_columns = [
    "fyllingsgrad",
    "kapasitet_TWh",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad",
]

plot_columns = [
    "fyllingsgrad",
    "kapasitet_TWh",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad",
]

rows = []

for col in plot_columns:
    rows.append({
        "variable": col,
        "first_month": first_month[col].tolist()
    })

tbl = pd.DataFrame(rows)

st.dataframe(
    tbl,
    column_config={
        "variable": "Variable",
        "first_month": st.column_config.LineChartColumn(
            "First month"
        ),
    },
    hide_index=True,
    width="stretch"
)