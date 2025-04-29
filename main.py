import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
from matplotlib import pyplot as plt
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure  # Updated import
from bson import ObjectId
from fire_detection import fire_detection_loop, save_chat_data
from occupancy_detection import occupancy_detection_loop, load_occupancy_data
from no_access_rooms import no_access_detection_loop, load_no_access_data

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
    db = client['vigil']
    cameras_collection = db['cameras']
    fire_settings_collection = db['fire_settings']
    occupancy_settings_collection = db['occupancy_settings']
    tailgating_settings_collection = db['tailgating_settings']
    no_access_settings_collection = db['no_access_settings']
    st.success("Connected to MongoDB Atlas successfully!")
except (ServerSelectionTimeoutError, ConnectionFailure) as e:  # Updated exception
    st.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
    st.write("**Troubleshooting Steps**:")
    st.write("1. Verify MongoDB Atlas credentials")
    st.write("2. Set Network Access to allow connections from your IP in MongoDB Atlas")
    st.write("3. Ensure pymongo>=4.8.0 is in requirements.txt")
    st.write("4. Check cluster status (not paused) in MongoDB Atlas")
    client = None
except Exception as e:
    st.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
    client = None

# [Rest of your code remains exactly the same...]

# Database Operations
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

# Utility Functions
def add_camera(name, address):
    """Add a camera to MongoDB and update session state."""
    if not name or not address:
        st.error("Camera name and address are required.")
        return
    if any(cam['name'] == name for cam in st.session_state.cameras):
        st.error("Camera name must be unique.")
        return
    camera = add_camera_to_db(name, address)
    if camera:
        st.session_state.cameras.append(camera)
        st.success(f"Added camera: {name}")

def remove_camera(index):
    """Remove a camera from MongoDB and update session state."""
    if 0 <= index < len(st.session_state.cameras):
        camera = st.session_state.cameras[index]
        remove_camera_from_db(camera['_id'])
        st.session_state.cameras.pop(index)
        st.session_state.confirm_remove = None
        st.success(f"Removed camera: {camera['name']}")

# Initialize session state
if 'cameras' not in st.session_state:
    st.session_state.cameras = get_cameras_from_db()
if 'confirm_remove' not in st.session_state:
    st.session_state.confirm_remove = None
if 'processing_active' not in st.session_state:
    st.session_state.processing_active = False
if 'fire_selected_cameras' not in st.session_state:
    st.session_state.fire_selected_cameras = get_selected_cameras(fire_settings_collection)
if 'occ_selected_cameras' not in st.session_state:
    st.session_state.occ_selected_cameras = get_selected_cameras(occupancy_settings_collection)
if 'tailgating_selected_cameras' not in st.session_state:
    st.session_state.tailgating_selected_cameras = get_selected_cameras(tailgating_settings_collection)
if 'no_access_selected_cameras' not in st.session_state:
    st.session_state.no_access_selected_cameras = get_selected_cameras(no_access_settings_collection)
if 'fire_detection_active' not in st.session_state:
    st.session_state.fire_detection_active = False
if 'telegram_status' not in st.session_state:
    st.session_state.telegram_status = []
if 'occ_detection_active' not in st.session_state:
    st.session_state.occ_detection_active = False
if 'occ_current_count' not in st.session_state:
    st.session_state.occ_current_count = 0
if 'occ_max_count' not in st.session_state:
    st.session_state.occ_max_count = 0
if 'occ_hourly_counts' not in st.session_state:
    st.session_state.occ_hourly_counts = [0] * 24
if 'occ_minute_counts' not in st.session_state:
    st.session_state.occ_minute_counts = [0] * 1440
if 'occ_last_update_hour' not in st.session_state:
    st.session_state.occ_last_update_hour = datetime.now().hour
if 'occ_last_update_minute' not in st.session_state:
    st.session_state.occ_last_update_minute = -1
if 'no_access_detection_active' not in st.session_state:
    st.session_state.no_access_detection_active = False

# App UI
st.title("📷 V.I.G.I.L - Video Intelligence for General Identification and Logging")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Camera Management", 
    "Fire Detection", 
    "Occupancy Dashboard", 
    "Tailgating", 
    "Unattended Bags",
    "No-Access Rooms"
])

with tab1:
    st.header("📹 Camera Management")
    st.write("Add, remove, and manage surveillance cameras connected to the system.")
    
    with st.expander("➕ Add New Camera", expanded=True):
        with st.form("add_camera_form"):
            name = st.text_input("Camera Name", help="A unique identifier for the camera")
            address = st.text_input("Camera Address", help="RTSP or HTTP stream URL")
            submitted = st.form_submit_button("Add Camera")
            if submitted:
                if name and address:
                    if any(cam['name'] == name for cam in st.session_state.cameras):
                        st.error("Camera name must be unique.")
                    else:
                        add_camera(name, address)
                        st.rerun()
                else:
                    st.error("Both camera name and address are required.")

    st.header("📋 Camera List")
    if not st.session_state.cameras:
        st.info("No cameras have been added yet. Add your first camera above.")
    else:
        for i, cam in enumerate(st.session_state.cameras):
            col1, col2, col3 = st.columns([4, 4, 2])
            with col1:
                st.markdown(f"**{cam['name']}**")
            with col2:
                st.code(cam['address'], language="text")
            with col3:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.confirm_remove = i

    if st.session_state.confirm_remove is not None:
        cam = st.session_state.cameras[st.session_state.confirm_remove]
        st.warning(f"Confirm removal of camera: {cam['name']}")
        st.write(f"Address: {cam['address']}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Removal"):
                remove_camera(st.session_state.confirm_remove)
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.confirm_remove = None
                st.rerun()

# [Rest of your tabs (tab2 through tab6) remain exactly the same as in your original code]
# ... include all the other tab implementations here ...

with tab2:
    # Fire Detection tab implementation
    pass

with tab3:
    # Occupancy Dashboard tab implementation
    pass

with tab4:
    # Tailgating tab implementation
    pass

with tab5:
    # Unattended Bags tab implementation
    pass

with tab6:
    # No-Access Rooms tab implementation
    pass
