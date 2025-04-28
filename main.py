import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
from matplotlib import pyplot as plt
from pymongo import MongoClient
from bson.objectid import ObjectId

# MongoDB Connection Setup
@st.cache_resource
def init_mongo_connection():
    try:
        client = MongoClient(st.secrets["mongodb"]["uri"])
        db = client[st.secrets["mongodb"]["dbname"]]
        # Create index on camera name to ensure uniqueness
        db.cameras.create_index("name", unique=True)
        return db
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        return None

# Initialize MongoDB connection
db = init_mongo_connection()

# Camera Management Functions
def add_camera_to_db(name, address):
    """Add a camera to MongoDB with validation"""
    if not db:
        st.error("Database connection not available")
        return False
    
    if not name or not address:
        st.warning("Please provide both name and address")
        return False
    
    try:
        db.cameras.insert_one({
            "name": name,
            "address": address,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        return True
    except Exception as e:
        if "duplicate key error" in str(e):
            st.warning(f"Camera '{name}' already exists")
        else:
            st.error(f"Error adding camera: {str(e)}")
        return False

def remove_camera_from_db(camera_id):
    """Remove a camera from MongoDB"""
    if not db:
        st.error("Database connection not available")
        return False
    
    try:
        result = db.cameras.delete_one({"_id": ObjectId(camera_id)})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error removing camera: {str(e)}")
        return False

def get_all_cameras_from_db():
    """Retrieve all cameras from MongoDB"""
    if not db:
        st.error("Database connection not available")
        return []
    
    try:
        return list(db.cameras.find().sort("created_at", -1))
    except Exception as e:
        st.error(f"Error fetching cameras: {str(e)}")
        return []

# Initialize session state with DB data
if 'cameras' not in st.session_state:
    st.session_state.cameras = get_all_cameras_from_db()

# [Rest of your session state initialization remains the same...]

# App UI
st.title("📷 V.I.G.I.L - Persistent Camera Management")

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
    
    # Add Camera Form
    with st.expander("➕ Add New Camera", expanded=True):
        with st.form("add_camera_form", clear_on_submit=True):
            name = st.text_input("Camera Name*", help="Unique identifier for the camera")
            address = st.text_input("Camera Address*", help="RTSP/HTTP stream URL or IP address")
            notes = st.text_area("Additional Notes", help="Optional description or location details")
            
            if st.form_submit_button("Add Camera"):
                if name and address:
                    if add_camera_to_db(name, address):
                        st.success(f"Camera '{name}' added successfully!")
                        # Update session state
                        st.session_state.cameras = get_all_cameras_from_db()
                        st.rerun()
                else:
                    st.warning("Please fill all required fields (*)")
    
    # Camera List
    st.header("📋 Configured Cameras")
    
    if not st.session_state.cameras:
        st.info("No cameras found. Add your first camera above.")
    else:
        for i, cam in enumerate(st.session_state.cameras):
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 5, 2])
                with col1:
                    st.subheader(cam["name"])
                    st.caption(f"Added: {cam['created_at'].strftime('%Y-%m-%d')}")
                with col2:
                    st.code(cam["address"])
                    if "notes" in cam and cam["notes"]:
                        st.markdown(f"*{cam['notes']}*")
                with col3:
                    if st.button("❌ Remove", key=f"remove_{i}"):
                        if remove_camera_from_db(str(cam["_id"])):
                            st.success(f"Camera '{cam['name']}' removed!")
                            st.session_state.cameras = get_all_cameras_from_db()
                            st.rerun()
                        else:
                            st.error("Failed to remove camera")

# [Rest of your tabs (tab2-tab6) remain unchanged...]

# ... (Previous code in main.py remains unchanged until tab2)

with tab2:
    st.header("🔥 Fire and Smoke Detection")
    
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
            st.session_state.fire_selected_cameras,
            key="fire_detection_cameras"
        )
        st.session_state.fire_selected_cameras = selected
        
        if st.session_state.fire_selected_cameras:
            st.subheader("✅ Selected Cameras")
            cols = st.columns(3)
            for i, cam_name in enumerate(st.session_state.fire_selected_cameras):
                with cols[i % 3]:
                    st.info(f"**{cam_name}**")
        
        st.markdown("---")
        st.subheader("🎬 Fire Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from fire_detection import fire_model
            if st.button("🔥 Start Fire Detection", 
                        disabled=not st.session_state.fire_selected_cameras or fire_model is None,
                        help="Start monitoring selected cameras for fire and smoke",
                        key="start_fire_detection"):
                st.session_state.fire_detection_active = True
                st.session_state.telegram_status = []
        with col2:
            if st.button("⏹️ Stop Detection", key="stop_fire_detection"):
                st.session_state.fire_detection_active = False
        
        if st.session_state.fire_selected_cameras:
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

with tab3:
    st.header("👥 Occupancy Dashboard")
    st.write("Track and display occupancy counts in monitored areas.")
    
    view_history = st.checkbox("View Historical Data", key="view_occupancy_history")
    
    if view_history:
        st.subheader("Historical Data")
        try:
            data = load_occupancy_data()
            date_options = sorted(list(data.keys()))
            if date_options:
                selected_date = st.selectbox("Select Date", date_options, key="occupancy_date_select")
                if selected_date:
                    doc = data[selected_date]
                    st.write(f"Maximum occupancy on {selected_date}: {doc['max_count']}")
                    
                    hist_fig, hist_ax = plt.subplots()
                    hours = [f"{h}:00" for h in range(24)]
                    hist_ax.plot(hours, doc["hourly_counts"], marker='o', color='orange')
                    hist_ax.set_title(f"Hourly Maximum Occupancy on {selected_date}")
                    hist_ax.set_xlabel("Hour of Day")
                    hist_ax.set_ylabel("Maximum People Count")
                    plt.xticks(rotation=45)
                    st.pyplot(hist_fig)
                    plt.close(hist_fig)
                    
                    hist_fig, hist_ax = plt.subplots(figsize=(10, 4))
                    minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
                    hist_ax.plot(range(1440), doc["minute_counts"], linewidth=1, color='orange')
                    hist_ax.set_title(f"Minute-by-Minute Presence on {selected_date}")
                    hist_ax.set_xlabel("Time (24h)")
                    hist_ax.set_ylabel("People Count")
                    hist_ax.set_xticks(range(0, 1440, 15*4))
                    hist_ax.set_xticklabels(minutes[::4], rotation=45)
                    st.pyplot(hist_fig)
                    plt.close(hist_fig)
            else:
                st.info("No historical occupancy data available")
        except Exception as e:
            st.error(f"Failed to load historical data: {e}")
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras for occupancy monitoring",
            [cam['name'] for cam in st.session_state.cameras],
            st.session_state.occ_selected_cameras,
            key="occupancy_cameras"
        )
        st.session_state.occ_selected_cameras = selected
        
        if st.session_state.occ_selected_cameras:
            st.subheader("✅ Selected Cameras")
            cols = st.columns(3)
            for i, cam_name in enumerate(st.session_state.occ_selected_cameras):
                with cols[i % 3]:
                    st.info(f"**{cam_name}**")
        
        st.markdown("---")
        st.subheader("🎬 Occupancy Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from occupancy_detection import occ_model
            if st.button("👥 Start Occupancy Tracking", 
                        disabled=not st.session_state.occ_selected_cameras or occ_model is None,
                        help="Start monitoring selected cameras for people counting",
                        key="start_occupancy_tracking"):
                st.session_state.occ_detection_active = True
        with col2:
            if st.button("⏹️ Stop Tracking", key="stop_occupancy_tracking"):
                st.session_state.occ_detection_active = False
        
        if st.session_state.occ_selected_cameras:
            st.subheader("📺 Live Feeds with Occupancy Count")
            video_placeholder = st.empty()
        
        stats_placeholder = st.empty()
        hourly_chart_placeholder = st.empty()
        minute_chart_placeholder = st.empty()
        
        if st.session_state.occ_detection_active:
            from occupancy_detection import occ_model
            if occ_model is None:
                st.error("Occupancy detection model not available")
            else:
                try:
                    asyncio.run(occupancy_detection_loop(
                        video_placeholder, stats_placeholder,
                        hourly_chart_placeholder, minute_chart_placeholder
                    ))
                except Exception as e:
                    st.error(f"Occupancy detection failed: {e}")
                    st.session_state.occ_detection_active = False


with tab4:
    st.header("🚪 Tailgating Detection")
    st.write("Detect unauthorized entry following authorized personnel.")
    
    # Initialize session state for tailgating
    if 'tailgating_selected_cameras' not in st.session_state:
        st.session_state.tailgating_selected_cameras = []
    if 'tailgating_detection_active' not in st.session_state:
        st.session_state.tailgating_detection_active = False
    
    # Historical data view
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
            st.session_state.tailgating_selected_cameras,
            key="tailgating_cameras"
        )
        st.session_state.tailgating_selected_cameras = selected
        
        if st.session_state.tailgating_selected_cameras:
            st.subheader("✅ Selected Cameras")
            cols = st.columns(3)
            for i, cam_name in enumerate(st.session_state.tailgating_selected_cameras):
                with cols[i % 3]:
                    st.info(f"**{cam_name}**")
        
        st.markdown("---")
        st.subheader("🎬 Tailgating Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from tailgating import tailgating_model
            if st.button("🚪 Start Tailgating Detection", 
                        disabled=not st.session_state.tailgating_selected_cameras or tailgating_model is None,
                        help="Start monitoring selected cameras for tailgating",
                        key="start_tailgating_detection"):
                st.session_state.tailgating_detection_active = True
        with col2:
            if st.button("⏹️ Stop Detection", key="stop_tailgating_detection"):
                st.session_state.tailgating_detection_active = False
        
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

# ... (Rest of main.py remains unchanged)

with tab5:
    st.header("👜 Unattended Bags Detection")
    st.write("Identify and alert about unattended bags in monitored areas.")
    if st.session_state.cameras:
        st.info("Unattended bags detection functionality would be implemented here")
    else:
        st.warning("Please add cameras first in the Camera Management tab")


with tab6:
    st.header("🔒 No-Access Rooms Detection")
    st.write("Detect and log human presence in restricted areas.")
    
    # Historical data view
    view_history = st.checkbox("View Historical Data", key="view_no_access_history")
    
    if view_history:
        st.subheader("Historical No-Access Events")
        data = load_no_access_data()
        date_options = list(data.keys())
        selected_date = st.selectbox("Select Date", date_options, key="no_access_date_select")
        
        if selected_date:
            events = data[selected_date]
            if events:
                df = pd.DataFrame(events, columns=["timestamp", "num_people", "camera_name"])
                df.columns = ["Timestamp", "Number of People", "Camera"]
                st.write(f"No-access events on {selected_date}:")
                st.dataframe(df)
            else:
                st.info(f"No no-access events recorded on {selected_date}")
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras for no-access room detection",
            [cam['name'] for cam in st.session_state.cameras],
            st.session_state.no_access_selected_cameras,
            key="no_access_cameras"
        )
        st.session_state.no_access_selected_cameras = selected
        
        if st.session_state.no_access_selected_cameras:
            st.subheader("✅ Selected Cameras")
            cols = st.columns(3)
            for i, cam_name in enumerate(st.session_state.no_access_selected_cameras):
                with cols[i % 3]:
                    st.info(f"**{cam_name}**")
        
        st.markdown("---")
        st.subheader("🎬 No-Access Detection Controls")
        col1, col2 = st.columns(2)
        with col1:
            from no_access_rooms import no_access_model
            if st.button("🔒 Start No-Access Detection", 
                        disabled=not st.session_state.no_access_selected_cameras or no_access_model is None,
                        help="Start monitoring selected cameras for human presence",
                        key="start_no_access_detection"):
                st.session_state.no_access_detection_active = True
        with col2:
            if st.button("⏹️ Stop Detection", key="stop_no_access_detection"):
                st.session_state.no_access_detection_active = False
        
        if st.session_state.no_access_selected_cameras:
            st.subheader("📺 Live Feeds with No-Access Detection")
            video_placeholder = st.empty()
            table_placeholder = st.empty()
        
            if st.session_state.no_access_detection_active:
                from no_access_rooms import no_access_model, no_access_detection_loop
                if no_access_model is None:
                    video_placeholder.error("No-access detection model not available")
                else:
                    selected_cams = [cam for cam in st.session_state.cameras 
                                   if cam['name'] in st.session_state.no_access_selected_cameras]
                    asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cams))
