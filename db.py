# db.py
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionError
import streamlit as st

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    # Test connection
    client.admin.command('ping')
    db = client['vigil_db']
    cameras_collection = db['cameras']
    fire_settings_collection = db['fire_settings']
    occupancy_settings_collection = db['occupancy_settings']
    tailgating_settings_collection = db['tailgating_settings']
    no_access_settings_collection = db['no_access_settings']
    st.success("Connected to MongoDB Atlas successfully!")
except (ServerSelectionTimeoutError, ConnectionError) as e:
    st.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
    st.write("**Troubleshooting Steps**:")
    st.write("1. Verify MongoDB Atlas URI (username, password, cluster name).")
    st.write("2. Set Network Access to 0.0.0.0/0 in MongoDB Atlas for testing.")
    st.write("3. Ensure pymongo>=4.8.0 is in requirements.txt.")
    st.write("4. Check cluster status (not paused) in MongoDB Atlas.")
    st.write("5. Run locally to isolate cloud-specific issues.")
    client = None  # Fallback to avoid crashes
except Exception as e:
    st.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
    client = None

def add_camera_to_db(name, address):
    """Add a camera to MongoDB."""
    if client is None:
        st.error("MongoDB not connected. Cannot add camera.")
        return None
    camera = {"name": name, "address": address}
    cameras_collection.insert_one(camera)
    return camera

def get_cameras_from_db():
    """Retrieve all cameras from MongoDB."""
    if client is None:
        return []
    return list(cameras_collection.find())

def remove_camera_from_db(camera_id):
    """Remove a camera from MongoDB by its ID."""
    if client is None:
        st.error("MongoDB not connected. Cannot remove camera.")
        return
    from bson import ObjectId
    cameras_collection.delete_one({"_id": ObjectId(camera_id)})

def save_selected_cameras(collection, selected_cameras):
    """Save selected cameras for a specific module."""
    if client is None:
        st.error("MongoDB not connected. Cannot save camera selections.")
        return
    collection.replace_one({}, {"selected_cameras": selected_cameras}, upsert=True)

def get_selected_cameras(collection):
    """Retrieve selected cameras for a specific module."""
    if client is None:
        return []
    doc = collection.find_one()
    return doc.get("selected_cameras", []) if doc else []
