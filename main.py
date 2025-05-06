

import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
import requests 
import time, json, os
import logging 
import numpy as np
import threading
from matplotlib import pyplot as plt
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from bson import ObjectId
from fire_detection import fire_detection_loop, save_chat_data
from occupancy_detection import occupancy_detection_loop, load_occupancy_data
from no_access_rooms import no_access_detection_loop, load_no_access_data


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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
except (ServerSelectionTimeoutError, ConnectionFailure) as e:
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

# Main App
st.title("📷 V.I.G.I.LLL - Video Intelligence for General Identification and Logging")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigation",
    ["Camera Management", "Fire Detection", "Occupancy Dashboard", "Tailgating", "No-Access Rooms"],
    key="navigation"
)

# Page 1: Camera Management
if page == "Camera Management":
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


# Page 2: Fire Detection
elif page == "Fire Detection":
    st.header("🔥 Fire and Smoke Detection")
    
    # Initialize detection state from MongoDB
    def get_fire_detection_state():
        if client is None:
            return False
        doc = fire_settings_collection.find_one({"type": "detection_state"})
        return doc.get("active", False) if doc else False
    
    def set_fire_detection_state(active):
        if client is None:
            return
        fire_settings_collection.update_one(
            {"type": "detection_state"},
            {"$set": {"active": active}},
            upsert=True
        )
    
    # Initialize session state from DB
    if 'fire_detection_active' not in st.session_state:
        st.session_state.fire_detection_active = get_fire_detection_state()
    
    # Force sync between session state and DB
    current_db_state = get_fire_detection_state()
    if st.session_state.fire_detection_active != current_db_state:
        st.session_state.fire_detection_active = current_db_state
        st.experimental_rerun()

    with st.expander("🔔 Telegram Notification Settings"):
        st.subheader("Manage Recipients")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Add New Recipient")
            new_name = st.text_input("Recipient Name", key="new_recipient_name")
            new_chat_id = st.text_input("Recipient Chat ID", key="new_chat_id")
            if st.button("Add Recipient", key="add_recipient") and new_name and new_chat_id:
                from fire_detection import chat_data, save_chat_data
                chat_data.append({"name": new_name, "chat_id": new_chat_id})
                save_chat_data()
                st.success(f"Added {new_name} (Chat ID: {new_chat_id})")
                st.rerun()
        
        with col2:
            st.subheader("Current Recipients")
            from fire_detection import chat_data, save_chat_data
            for i, recipient in enumerate(chat_data):
                st.write(f"Name: {recipient['name']}, Chat ID: {recipient['chat_id']}")
                if st.button(f"Remove {recipient['name']}", key=f"remove_recipient_{i}"):
                    chat_data.pop(i)
                    save_chat_data()
                    st.rerun()
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras to monitor for fire/smoke",
            [cam['name'] for cam in st.session_state.cameras],
            default=st.session_state.fire_selected_cameras,
            key="fire_detection_cameras"
        )
        if selected != st.session_state.fire_selected_cameras:
            st.session_state.fire_selected_cameras = selected
            save_selected_cameras(fire_settings_collection, selected)
        
        # Show active status and cameras
        if st.session_state.fire_detection_active:
            st.subheader("🟢 Detection Active")
            if st.session_state.fire_selected_cameras:
                st.subheader("✅ Active Cameras")
                cols = st.columns(3)
                for i, cam_name in enumerate(st.session_state.fire_selected_cameras):
                    with cols[i % 3]:
                        st.success(f"🔴 LIVE: {cam_name}")
        
        st.markdown("---")
        st.subheader("🎬 Fire Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from fire_detection import fire_model
            if st.button("🔥 Start Fire Detection", 
                        disabled=st.session_state.fire_detection_active or not st.session_state.fire_selected_cameras or fire_model is None,
                        help="Start monitoring selected cameras for fire and smoke",
                        key="start_fire_detection"):
                st.session_state.fire_detection_active = True
                set_fire_detection_state(True)  # Persist to DB
                st.session_state.telegram_status = []
                st.experimental_rerun()
        with col2:
            if st.button("⏹️ Stop Detection", 
                        disabled=not st.session_state.fire_detection_active,
                        key="stop_fire_detection"):
                st.session_state.fire_detection_active = False
                set_fire_detection_state(False)  # Persist to DB
                st.experimental_rerun()
        
        if st.session_state.fire_selected_cameras and st.session_state.fire_detection_active:
            st.subheader("📺 Live Feeds with Fire Detection")
            video_placeholder = st.empty()
        
        status_placeholder = st.empty()
        
        if st.session_state.fire_detection_active:
            from fire_detection import fire_model
            if fire_model is None:
                status_placeholder.error("Fire detection model not available")
            else:
                status_placeholder.info("Fire detection active - monitoring selected cameras...")
                asyncio.run(fire_detection_loop(video_placeholder, status_placeholder))
        
        if st.session_state.telegram_status:
            status_placeholder.write("### Notification Status")
            for msg in st.session_state.telegram_status[-5:]:
                status_placeholder.write(msg)
        
        st.markdown("---")
        st.subheader("ℹ️ How to Find Your Telegram Chat ID")
        st.write("1. Start a chat with @userinfobot on Telegram")
        st.write("2. Send any message to the bot")
        st.write("3. The bot will reply with your chat ID")
        
# Page 3: Occupancy Dashboard
#######################################
# Page 3: Occupancy Dashboard
elif page == "Occupancy Dashboard":
    st.header("👥 Occupancy Dashboard")
    
    # Initialize detection state (no MongoDB, use session state only)
    def get_occupancy_detection_state():
        return st.session_state.get('occ_detection_active', False)
    
    def set_occupancy_detection_state(active):
        st.session_state.occ_detection_active = active
    
    # JSON file paths
    OCCUPANCY_JSON_FILE = "occupancy_data.json"
    SETTINGS_JSON_FILE = "settings.json"
    
    # Function to load data from JSON
    def load_occupancy_data(date=None):
        try:
            if not os.path.exists(OCCUPANCY_JSON_FILE):
                logger.info(f"No JSON file found at {OCCUPANCY_JSON_FILE}. Creating empty file.")
                with open(OCCUPANCY_JSON_FILE, 'w') as f:
                    json.dump({}, f)
                return {}
            
            with open(OCCUPANCY_JSON_FILE, 'r') as f:
                data = json.load(f)
            
            # Validate data structure
            validated_data = {}
            for date_str, cameras in data.items():
                if not isinstance(cameras, dict):
                    logger.warning(f"Skipping invalid data for date {date_str}: not a dictionary")
                    continue
                validated_cameras = {}
                for cam_name, cam_data in cameras.items():
                    if not all(key in cam_data for key in ['presence', 'hourly_max_counts']):
                        logger.warning(f"Skipping invalid data for {date_str}, {cam_name}: missing fields")
                        continue
                    if not (isinstance(cam_data['presence'], list) and len(cam_data['presence']) == 1440 and
                            isinstance(cam_data['hourly_max_counts'], list) and len(cam_data['hourly_max_counts']) == 24):
                        logger.warning(f"Skipping invalid data for {date_str}, {cam_name}: incorrect field lengths")
                        continue
                    validated_cameras[cam_name] = cam_data
                if validated_cameras:
                    validated_data[date_str] = validated_cameras
            
            if date:
                date_str = str(date)
                return {date_str: validated_data.get(date_str, {})} if date_str in validated_data else {}
            return validated_data
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse JSON data: {e}")
            logger.error(f"Failed to parse JSON data: {e}")
            try:
                with open(OCCUPANCY_JSON_FILE, 'r') as f:
                    invalid_content = f.read()
                logger.error(f"Invalid JSON content: {invalid_content}")
            except Exception as read_e:
                logger.error(f"Failed to read invalid JSON file: {read_e}")
            # Reset file to empty
            try:
                with open(OCCUPANCY_JSON_FILE, 'w') as f:
                    json.dump({}, f)
                logger.info("Reset JSON file to empty due to parsing error")
            except Exception as write_e:
                logger.error(f"Failed to reset JSON file: {write_e}")
            return {}
        except Exception as e:
            st.error(f"Failed to load JSON data: {e}")
            logger.error(f"Failed to load JSON data: {e}")
            return {}
    
    # Function to insert default data into JSON
    def insert_default_data():
        for _ in range(3):  # Retry up to 3 times
            try:
                data = load_occupancy_data()
                default_dates = ["2025-05-04", "2025-05-05"]
                cameras = ["Cam Road", "Cam Hall"]
                
                for default_date in default_dates:
                    if default_date not in data:
                        data[default_date] = {}
                    for camera_name in cameras:
                        # Skip if valid data already exists
                        if (default_date in data and camera_name in data[default_date] and
                            isinstance(data[default_date][camera_name].get('presence'), list) and
                            len(data[default_date][camera_name]['presence']) == 1440 and
                            isinstance(data[default_date][camera_name].get('hourly_max_counts'), list) and
                            len(data[default_date][camera_name]['hourly_max_counts']) == 24):
                            logger.info(f"Default data for {default_date}, {camera_name} already exists")
                            continue
                        
                        # Create sample data
                        presence = [0] * 1440
                        hourly_max_counts = [0] * 24
                        
                        if default_date == "2025-05-04":
                            for minute in range(420, 660):  # 7:00 to 11:00
                                presence[minute] = int(np.random.choice([0, 1], p=[0.4, 0.6]))
                            for minute in range(900, 1080):  # 15:00 to 18:00
                                presence[minute] = int(np.random.choice([0, 1], p=[0.5, 0.5]))
                            for hour in range(24):
                                max_count = int(max(np.random.randint(0, 8, size=10))) if hour in range(7, 11) or hour in range(15, 18) else 0
                                hourly_max_counts[hour] = max_count
                        else:  # 2025-05-05
                            for minute in range(480, 720):  # 8:00 to 12:00
                                presence[minute] = int(np.random.choice([0, 1], p=[0.3, 0.7]))
                            for minute in range(840, 1020):  # 14:00 to 17:00
                                presence[minute] = int(np.random.choice([0, 1], p=[0.4, 0.6]))
                            for hour in range(24):
                                max_count = int(max(np.random.randint(0, 10, size=10))) if hour in range(8, 12) or hour in range(14, 17) else 0
                                hourly_max_counts[hour] = max_count
                        
                        data[default_date][camera_name] = {
                            "presence": presence,
                            "hourly_max_counts": hourly_max_counts
                        }
                
                with open(OCCUPANCY_JSON_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info("Default data inserted into JSON file")
                return True
            except Exception as e:
                st.warning(f"Retry failed to insert default data: {e}")
                logger.error(f"Retry failed to insert default data: {e}")
        st.error("Failed to insert default data after retries")
        logger.error("Failed to insert default data after retries")
        return False
    
    # Function to clear invalid data from JSON
    def clear_invalid_data():
        try:
            if os.path.exists(OCCUPANCY_JSON_FILE):
                os.remove(OCCUPANCY_JSON_FILE)
                logger.info(f"Deleted {OCCUPANCY_JSON_FILE}")
            with open(OCCUPANCY_JSON_FILE, 'w') as f:
                json.dump({}, f)
            st.success("Cleared invalid data and reset JSON file")
            logger.info("Cleared invalid data and reset JSON file")
            return True
        except Exception as e:
            st.error(f"Failed to clear invalid data: {e}")
            logger.error(f"Failed to clear invalid data: {e}")
            return False
    
    # Function to save selected cameras to JSON
    def save_selected_cameras(selected):
        try:
            if not os.path.exists(SETTINGS_JSON_FILE):
                with open(SETTINGS_JSON_FILE, 'w') as f:
                    json.dump({}, f)
            with open(SETTINGS_JSON_FILE, 'r') as f:
                settings = json.load(f)
            settings['selected_cameras'] = selected
            with open(SETTINGS_JSON_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info("Saved selected cameras to settings.json")
        except Exception as e:
            st.error(f"Failed to save selected cameras: {e}")
            logger.error(f"Failed to save selected cameras: {e}")
    
    # Function to load selected cameras from JSON
    def load_selected_cameras():
        try:
            if not os.path.exists(SETTINGS_JSON_FILE):
                return []
            with open(SETTINGS_JSON_FILE, 'r') as f:
                settings = json.load(f)
            return settings.get('selected_cameras', [])
        except Exception as e:
            logger.error(f"Failed to load selected cameras: {e}")
            return []
    
    # Function to update real-time occupancy data in JSON
    def update_occupancy_data_json(camera_name, presence, hourly_max_counts, current_count, current_minute, current_hour):
        try:
            data = load_occupancy_data()
            today = str(datetime.now().date())
            
            if today not in data:
                data[today] = {}
            if camera_name not in data[today]:
                data[today][camera_name] = {
                    "presence": [0] * 1440,
                    "hourly_max_counts": [0] * 24
                }
            
            # Update presence and hourly max counts
            data[today][camera_name]['presence'][current_minute] = 1 if current_count > 0 else data[today][camera_name]['presence'][current_minute]
            data[today][camera_name]['hourly_max_counts'][current_hour] = max(
                data[today][camera_name]['hourly_max_counts'][current_hour], int(current_count)
            )
            
            # Atomic write to prevent corruption
            with open(OCCUPANCY_JSON_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Updated real-time data for {today}, {camera_name}")
            return data[today][camera_name]['presence'], data[today][camera_name]['hourly_max_counts']
        except Exception as e:
            st.warning(f"Failed to update real-time data for {camera_name}: {e}")
            logger.error(f"Failed to update real-time data for {camera_name}: {e}")
            return presence, hourly_max_counts
    
    # Initialize session state
    if 'occ_detection_active' not in st.session_state:
        st.session_state.occ_detection_active = get_occupancy_detection_state()
    if 'occ_selected_cameras' not in st.session_state:
        st.session_state.occ_selected_cameras = load_selected_cameras()
    
    # Force sync (no DB, just session state)
    current_state = get_occupancy_detection_state()
    if st.session_state.occ_detection_active != current_state:
        st.session_state.occ_detection_active = current_state
        st.experimental_rerun()

    st.write("Track and display occupancy counts in monitored areas.")
    
    # JSON data management interface
    st.sidebar.header("Data Management")
    if st.sidebar.button("Reset Data and Insert Defaults"):
        if clear_invalid_data():
            if insert_default_data():
                st.success("Default data inserted for 2025-05-04 and 2025-05-05")
                st.experimental_rerun()
    
    view_history = st.checkbox("View Historical Data", key="view_occupancy_history")
    
    if view_history:
        st.subheader("Historical Data")
        try:
            from occupancy_detection import plot_presence_clock, plot_hourly_occupancy
            data = load_occupancy_data()
            date_options = sorted(list(data.keys()))
            if date_options:
                selected_date = st.selectbox("Select Date", date_options, key="occupancy_date_select")
                if selected_date in data:
                    st.write(f"### Data for {selected_date}")
                    for camera_name in data[selected_date]:
                        st.write(f"#### {camera_name}")
                        col1, col2 = st.columns(2)
                        
                        # Minute-by-minute presence (circular clock)
                        with col1:
                            fig = plot_presence_clock(
                                data[selected_date][camera_name]['presence'],
                                camera_name, selected_date
                            )
                            st.pyplot(fig)
                            plt.close(fig)
                        
                        # Hourly maximum occupancy
                        with col2:
                            fig = plot_hourly_occupancy(
                                data[selected_date][camera_name]['hourly_max_counts'],
                                camera_name, selected_date
                            )
                            st.pyplot(fig)
                            plt.close(fig)
                else:
                    st.error(f"No data found for {selected_date}.")
            else:
                st.warning("No historical occupancy data available. Attempting to insert default data...")
                if clear_invalid_data():
                    if insert_default_data():
                        st.success("Default data inserted successfully")
                        data = load_occupancy_data()
                        date_options = sorted(list(data.keys()))
                        if date_options:
                            st.experimental_rerun()
                        else:
                            st.error("Failed to insert default data.")
                    else:
                        st.error("Failed to insert default data.")
                    st.write("**Troubleshooting Steps**:")
                    st.write("1. Ensure write permissions for the app directory.")
                    st.write("2. Check logs for file access errors.")
                    st.write("3. Use 'Reset Data and Insert Defaults' button.")
                    st.write("4. Verify occupancy_data.json exists in the repository.")
        except Exception as e:
            st.error(f"Failed to load historical data: {e}")
            st.write("**Troubleshooting Steps**:")
            st.write("1. Ensure occupancy_detection.py is correctly implemented.")
            st.write("2. Verify occupancy_data.json is accessible.")
            st.write("3. Check for file corruption or permission issues.")
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras for occupancy monitoring",
            [cam['name'] for cam in st.session_state.cameras],
            default=st.session_state.occ_selected_cameras,
            key="occupancy_cameras"
        )
        if selected != st.session_state.occ_selected_cameras:
            st.session_state.occ_selected_cameras = selected
            save_selected_cameras(selected)
        
        # Show active status and cameras
        if st.session_state.occ_detection_active:
            st.subheader("🟢 Detection Active")
            if st.session_state.occ_selected_cameras:
                st.subheader("✅ Active Cameras")
                cols = st.columns(3)
                for i, cam_name in enumerate(st.session_state.occ_selected_cameras):
                    with cols[i % 3]:
                        st.success(f"🔴 LIVE: {cam_name}")
        
        st.markdown("---")
        st.subheader("🎬 Occupancy Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from occupancy_detection import occ_model
            if st.button("👥 Start Occupancy Tracking", 
                        disabled=st.session_state.occ_detection_active or not st.session_state.occ_selected_cameras or occ_model is None,
                        help="Start monitoring selected cameras for people counting",
                        key="start_occupancy_tracking"):
                st.session_state.occ_detection_active = True
                set_occupancy_detection_state(True)
                st.experimental_rerun()
        with col2:
            if st.button("⏹️ Stop Tracking", 
                        disabled=not st.session_state.occ_detection_active,
                        key="stop_occupancy_tracking"):
                st.session_state.occ_detection_active = False
                set_occupancy_detection_state(False)
                st.experimental_rerun()
        
        if st.session_state.occ_selected_cameras and st.session_state.occ_detection_active:
            st.subheader("📺 Live Feeds with Occupancy Count")
            video_placeholder = st.empty()
        
        stats_placeholder = st.empty()
        
        if st.session_state.occ_detection_active:
            from occupancy_detection import occ_model, occupancy_detection_loop
            if occ_model is None:
                st.error("Occupancy detection model not available")
            else:
                try:
                    asyncio.run(occupancy_detection_loop(
                        video_placeholder, stats_placeholder, update_occupancy_data_json
                    ))
                except Exception as e:
                    st.error(f"Occupancy detection failed: {e}")
                    st.session_state.occ_detection_active = False
                    set_occupancy_detection_state(False)
                    st.experimental_rerun()


# Page 4: Tailgating
elif page == "Tailgating":
    st.header("🚪 Tailgating Detection")
    
    # Initialize detection state from MongoDB
    def get_tailgating_detection_state():
        if client is None:
            return False
        doc = tailgating_settings_collection.find_one({"type": "detection_state"})
        return doc.get("active", False) if doc else False
    
    def set_tailgating_detection_state(active):
        if client is None:
            return
        tailgating_settings_collection.update_one(
            {"type": "detection_state"},
            {"$set": {"active": active}},
            upsert=True
        )
    
    # Initialize session state from DB
    if 'tailgating_detection_active' not in st.session_state:
        st.session_state.tailgating_detection_active = get_tailgating_detection_state()
    
    # Force sync between session state and DB
    current_db_state = get_tailgating_detection_state()
    if st.session_state.tailgating_detection_active != current_db_state:
        st.session_state.tailgating_detection_active = current_db_state
        st.experimental_rerun()

    st.write("Detect unauthorized entry following authorized personnel.")
    
    view_history = st.checkbox("View Historical Data", key="view_tailgating_history")
    
    if view_history:
        st.subheader("Historical Tailgating Events")
        from tailgating import load_tailgating_data
        data = load_tailgating_data()
        date_options = list(data.keys())
        selected_date = st.selectbox("Select Date", date_options, key="tailgating_date_select")
        
        if selected_date:
            events = data[selected_date]
            if events:
                df = pd.DataFrame(events, columns=["timestamp", "num_people", "camera_name"])
                df.columns = ["Timestamp", "Number of People", "Camera"]
                st.write(f"Tailgating events on {selected_date}:")
                st.dataframe(df)
            else:
                st.info(f"No tailgating events recorded on {selected_date}")
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras for tailgating detection",
            [cam['name'] for cam in st.session_state.cameras],
            default=st.session_state.tailgating_selected_cameras,
            key="tailgating_cameras"
        )
        if selected != st.session_state.tailgating_selected_cameras:
            st.session_state.tailgating_selected_cameras = selected
            save_selected_cameras(tailgating_settings_collection, selected)
        
        # Show active status and cameras
        if st.session_state.tailgating_detection_active:
            st.subheader("🟢 Detection Active")
            if st.session_state.tailgating_selected_cameras:
                st.subheader("✅ Active Cameras")
                cols = st.columns(3)
                for i, cam_name in enumerate(st.session_state.tailgating_selected_cameras):
                    with cols[i % 3]:
                        st.success(f"🔴 LIVE: {cam_name}")
        
        st.markdown("---")
        st.subheader("🎬 Tailgating Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from tailgating import tailgating_model
            if st.button("🚪 Start Tailgating Detection", 
                        disabled=st.session_state.tailgating_detection_active or not st.session_state.tailgating_selected_cameras or tailgating_model is None,
                        help="Start monitoring selected cameras for tailgating",
                        key="start_tailgating_detection"):
                st.session_state.tailgating_detection_active = True
                set_tailgating_detection_state(True)
                st.experimental_rerun()
        with col2:
            if st.button("⏹️ Stop Detection", 
                        disabled=not st.session_state.tailgating_detection_active,
                        key="stop_tailgating_detection"):
                st.session_state.tailgating_detection_active = False
                set_tailgating_detection_state(False)
                st.experimental_rerun()
        
        if st.session_state.tailgating_selected_cameras:
            st.subheader("📺 Live Feeds with Tailgating Detection")
            video_placeholder = st.empty()
            table_placeholder = st.empty()
        
            if st.session_state.tailgating_detection_active:
                from tailgating import tailgating_model, tailgating_detection_loop
                if tailgating_model is None:
                    video_placeholder.error("Tailgating detection model not available")
                else:
                    selected_cams = [cam for cam in st.session_state.cameras 
                                   if cam['name'] in st.session_state.tailgating_selected_cameras]
                    asyncio.run(tailgating_detection_loop(video_placeholder, table_placeholder, selected_cams))






elif page == "No-Access Rooms":
    st.header("🔒 No-Access Rooms Detection")
    
    # Initialize detection state from MongoDB
    def get_no_access_detection_state():
        if client is None:
            return False
        doc = no_access_settings_collection.find_one({"type": "detection_state"})
        return doc.get("active", False) if doc else False
    
    def set_no_access_detection_state(active):
        if client is None:
            return
        no_access_settings_collection.update_one(
            {"type": "detection_state"},
            {"$set": {"active": active}},
            upsert=True
        )
    
    # Initialize session state from DB
    if 'no_access_detection_active' not in st.session_state:
        st.session_state.no_access_detection_active = get_no_access_detection_state()
    
    # Force sync between session state and DB
    current_db_state = get_no_access_detection_state()
    if st.session_state.no_access_detection_active != current_db_state:
        st.session_state.no_access_detection_active = current_db_state
        st.experimental_rerun()

    # Check model availability
    try:
        from no_access_rooms import no_access_model
        model_available = no_access_model is not None
    except (ImportError, AttributeError):
        model_available = False
        st.warning("No-access detection model not available. Please check the model file.")

    st.write("Detect and log human presence in restricted areas.")
        
    view_history = st.checkbox("View Historical Data", key="view_no_access_history")
    
    if view_history:
        st.subheader("Historical No-Access Events")
        
        from no_access_rooms import load_no_access_data, get_available_dates
        
        available_dates = get_available_dates()
        if not available_dates:
            st.warning("No historical data available yet")
        else:
            selected_date = st.selectbox("Select date", available_dates)
            historical_data = load_no_access_data(date_filter=selected_date)
            
            if historical_data:
                st.success(f"Data for {selected_date}")
                df = pd.DataFrame(historical_data[selected_date])
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download CSV",
                    csv,
                    f"detections_{selected_date}.csv",
                    "text/csv"
                )
            else:
                st.warning(f"No data for {selected_date}")
        
        st.stop()
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras for no-access room detection",
            [cam['name'] for cam in st.session_state.cameras],
            default=st.session_state.no_access_selected_cameras,
            key="no_access_cameras"
        )
        if selected != st.session_state.no_access_selected_cameras:
            st.session_state.no_access_selected_cameras = selected
            save_selected_cameras(no_access_settings_collection, selected)
        
        # Show active status and cameras
        if st.session_state.no_access_detection_active:
            st.subheader("🟢 Detection Active")
            if st.session_state.no_access_selected_cameras:
                st.subheader("✅ Active Cameras")
                cols = st.columns(3)
                for i, cam_name in enumerate(st.session_state.no_access_selected_cameras):
                    with cols[i % 3]:
                        st.success(f"🔴 LIVE: {cam_name}")
        
        st.markdown("---")
        st.subheader("🎬 No-Access Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔒 Start No-Access Detection", 
                        disabled=(st.session_state.no_access_detection_active or 
                                 not st.session_state.no_access_selected_cameras or 
                                 not model_available),
                        help="Start monitoring selected cameras for human presence",
                        key="start_no_access_detection"):
                if not model_available:
                    st.error("Detection model not available - cannot start monitoring")
                else:
                    st.session_state.no_access_detection_active = True
                    set_no_access_detection_state(True)
                    st.experimental_rerun()
        with col2:
            if st.button("⏹️ Stop Detection", 
                        disabled=not st.session_state.no_access_detection_active,
                        key="stop_no_access_detection"):
                st.session_state.no_access_detection_active = False
                set_no_access_detection_state(False)
                st.experimental_rerun()
        
        if st.session_state.no_access_selected_cameras:
            st.subheader("📺 Live Feeds with No-Access Detection")
            video_placeholder = st.empty()
            table_placeholder = st.empty()
        
            if st.session_state.no_access_detection_active:
                if not model_available:
                    video_placeholder.error("No-access detection model not available")
                else:
                    try:
                        from no_access_rooms import no_access_detection_loop
                        selected_cams = [cam for cam in st.session_state.cameras 
                                       if cam['name'] in st.session_state.no_access_selected_cameras]
                        asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cams))
                    except Exception as e:
                        video_placeholder.error(f"Failed to start detection: {str(e)}")
                        st.session_state.no_access_detection_active = False
                        set_no_access_detection_state(False)
                        st.experimental_rerun()
