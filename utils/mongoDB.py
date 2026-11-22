"""MongoDB Atlas connection and electricity data loading."""

import streamlit as st
from pymongo import MongoClient
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)


# Create a MongoDB client using the configured connection.
@st.cache_resource
def get_mongo_client() -> MongoClient:
    """Connect to MongoDB Atlas and verify the connection."""
    try:
        mongo_uri = st.secrets["mongo_uri"]
    except (KeyError, FileNotFoundError) as exc:
        raise RuntimeError(
            "MongoDB configuration is missing. "
            "Please add 'mongo_uri' to your Streamlit secrets."
        ) from exc

    if not mongo_uri:
        raise RuntimeError("MongoDB connection URI is empty.")

    client = None
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        return client
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        if client is not None:
            client.close()
        raise RuntimeError(
            "Could not connect to MongoDB Atlas. "
            "Please check the database connection and try again."
        ) from exc
    except (ConfigurationError, OperationFailure) as exc:
        if client is not None:
            client.close()
        raise RuntimeError(
            "MongoDB connection configuration or authentication failed. "
            "Please check your database settings."
        ) from exc
    except PyMongoError as exc:
        if client is not None:
            client.close()
        raise RuntimeError(
            "An unexpected MongoDB connection error occurred."
        ) from exc


# Retrieve electricity flow observations from MongoDB.
@st.cache_data(ttl=3600, show_spinner="Loading electricity data...")
def load_electricity_data() -> list[dict]:
    """Load electricity flow documents from MongoDB Atlas."""
    client = get_mongo_client()

    try:
        db = client["IND320"]
        collection = db["crossboarder_flows"]
        documents = list(collection.find({}, {"_id": 0}))
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        raise RuntimeError(
            "The MongoDB connection was lost while loading electricity data. "
            "Please try again."
        ) from exc
    except OperationFailure as exc:
        raise RuntimeError(
            "MongoDB could not read the electricity data. "
            "Please check database access permissions."
        ) from exc
    except PyMongoError as exc:
        raise RuntimeError(
            "An error occurred while retrieving electricity data from MongoDB."
        ) from exc

    if not documents:
        raise ValueError(
            "No electricity flow data was found in the MongoDB collection "
            "'IND320.crossboarder_flows'."
        )

    return documents
