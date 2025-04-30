import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
import requests 
import time
import threading
from matplotlib import pyplot as plt
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure  # Updated import
from bson import ObjectId
from fire_detection import fire_detection_loop, save_chat_data
from occupancy_detection import occupancy_detection_loop, load_occupancy_data
from no_access_rooms import no_access_detection_loop, load_no_access_data



def keep_alive():
    while True:
        try:
            # Replace with your actual Streamlit Cloud URL
            requests.get("https://vigilpro.streamlit.app/")  
            time.sleep(900)  # Ping every 15 minutes (900 seconds)
        except:
            pass

# 2. Start the thread (daemon=True allows it to run in background)
threading.Thread(target=keep_alive, daemon=True).start()


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
st.title("📷 V.I.G.I.LLL - Video Intelligence for General Identification and Logging")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Camera Management", 
    "Fire Detection", 
    "Occupancy Dashboard", 
    "Tailgating", 
    "Unattended Bags",
    "No-Access Rooms",
    "hello"
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
            default=st.session_state.fire_selected_cameras,
            key="fire_detection_cameras"
        )
        if selected != st.session_state.fire_selected_cameras:
            st.session_state.fire_selected_cameras = selected
            save_selected_cameras(fire_settings_collection, selected)
        
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
            default=st.session_state.occ_selected_cameras,
            key="occupancy_cameras"
        )
        if selected != st.session_state.occ_selected_cameras:
            st.session_state.occ_selected_cameras = selected
            save_selected_cameras(occupancy_settings_collection, selected)
        
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

with tab5:
    st.header("👜 Unattended Bags Detection")
    st.write("This feature is under development.")
    st.info("Coming soon: Detect unattended bags in monitored areas.")
        
with tab6:
    st.header("🔒 No-Access Rooms Detection")
    st.write("Detect and log human presence in restricted areas.")
    
    view_history = st.checkbox("View Historical Data", key="view_no_access_history")
    
    if view_history:
        st.subheader("Historical No-Access Events")
        
        # Add view options (by date or month)
        view_option = st.radio("View by:", ["Date", "Month"], key="no_access_view_option")
        
        if view_option == "Date":
            available_dates = get_available_dates()
            if available_dates:
                selected_date = st.selectbox("Select Date", available_dates, key="no_access_date_select")
                if selected_date:
                    data = load_no_access_data(date_filter=selected_date)
                    if data and selected_date in data:
                        events = data[selected_date]
                        df = pd.DataFrame(events)
                        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        st.write(f"No-access events on {selected_date}:")
                        st.dataframe(df)
                        
                        # Show snapshots if available
                        if 'has_snapshot' in df.columns:
                            selected_event = st.selectbox("View snapshot for event:", 
                                                         df['timestamp'].tolist(),
                                                         key="no_access_event_select")
                            if selected_event:
                                event_data = no_access_collection.find_one({
                                    'date': selected_date,
                                    'timestamp': datetime.strptime(selected_event, '%Y-%m-%d %H:%M:%S')
                                })
                                if event_data and 'snapshot' in event_data:
                                    snapshot = cv2.imdecode(np.frombuffer(event_data['snapshot'], cv2.IMREAD_COLOR))
                                    st.image(snapshot, channels="BGR", caption=f"Snapshot from {selected_event}")
                    else:
                        st.info(f"No no-access events recorded on {selected_date}")
            else:
                st.info("No no-access events recorded yet")
                
        else:  # Month view
            available_months = get_available_months()
            if available_months:
                selected_month = st.selectbox("Select Month", available_months, key="no_access_month_select")
                if selected_month:
                    data = load_no_access_data(month_filter=selected_month)
                    if data:
                        # Create summary statistics
                        all_events = []
                        for date_events in data.values():
                            all_events.extend(date_events)
                        
                        df = pd.DataFrame(all_events)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df['date'] = df['timestamp'].dt.date
                        
                        st.write(f"No-access events summary for {selected_month}:")
                        
                        # Show daily counts
                        daily_counts = df.groupby('date').agg({
                            'num_people': 'sum',
                            'camera_name': 'count'
                        }).rename(columns={
                            'num_people': 'Total People Detected',
                            'camera_name': 'Event Count'
                        })
                        st.bar_chart(daily_counts['Event Count'])
                        
                        # Show camera-wise distribution
                        st.write("Camera-wise distribution:")
                        cam_counts = df.groupby('camera_name').size().reset_index(name='Count')
                        st.bar_chart(cam_counts.set_index('camera_name'))
                        
                        # Show detailed events
                        st.write("Detailed events:")
                        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        st.dataframe(df[['timestamp', 'num_people', 'camera_name']])
                    else:
                        st.info(f"No no-access events recorded in {selected_month}")
            else:
                st.info("No no-access events recorded yet")
    
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
                if no_access_model is None:
                    video_placeholder.error("No-access detection model not available")
                else:
                    selected_cams = [cam for cam in st.session_state.cameras 
                                   if cam['name'] in st.session_state.no_access_selected_cameras]
                    asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cams))

with tab7:
    st.header("📹 Camera Hello this is a new camera system")
    st.write("you definitely have the power to resolve this system with many more such things to do.")
    
