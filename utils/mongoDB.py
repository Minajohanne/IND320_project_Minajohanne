import streamlit as st
from pymongo import MongoClient


@st.cache_resource
def get_mongo_client():
    """Establish a connection to MongoDB Atlas."""
    return MongoClient(st.secrets["mongo_uri"])


@st.cache_data
def load_electricity_data():
    """Load electricity flow data from MongoDB."""
    client = get_mongo_client()

    db = client["IND320"]
    collection = db["crossboarder_flows"]

    # Return a list of all documents in the collection, excluding the _id field
    return list(collection.find({}, {"_id": 0}))