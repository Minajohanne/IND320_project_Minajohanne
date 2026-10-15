import streamlit as st
import pandas as pd
from utils.mongoDB import load_electricity_data

st.title("Electricity flows")

# Load data from MongoDB
data = load_electricity_data()
df = pd.DataFrame(data)

# Split the page into two columns
col1, col2 = st.columns(2, gap="large")