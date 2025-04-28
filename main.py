import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
from matplotlib import pyplot as plt

# ==============================================
# UTILITY FUNCTIONS (Originally from utils.py)
# ==============================================

def add_camera(name, address):
    """Add a new camera to the session state"""
    if not name or not address:
        st.error("Both name and address are required")
        return
    
    # Check if camera already exists
    for cam in st.session_state.cameras:
        if cam['name'] == name or cam['address'] == address:
            st.error("Camera with this name or address already exists")
            return
    
    # Add new camera
    st.session_state.cameras.append({
        'name': name,
        'address': address,
        'enabled': True
    })
    st.success(f"Camera '{name}' added successfully")

def remove_camera(index):
    """Remove a camera from the session state"""
    if 0 <= index < len(st.session_state.cameras):
        removed_cam = st.session_state.cameras.pop(index)
        st.success(f"Camera '{removed_cam['name']}' removed successfully")
        st.session_state.confirm_remove = None
    else:
        st.error("Invalid camera index")

def get_camera_by_name(name):
    """Get camera details by name"""
    for cam in st.session_state.cameras:
        if cam['name'] == name:
            return cam
    return None

def get_enabled_cameras():
    """Get list of enabled cameras"""
    return [cam for cam in st.session_state.cameras if cam['enabled']]

def toggle_camera_status(name, enabled):
    """Enable/disable a camera"""
    for cam in st.session_state.cameras:
        if cam['name'] == name:
            cam['enabled'] = enabled
            status = "enabled" if enabled else "disabled"
            st.success(f"Camera '{name}' {status}")
            return
    st.error(f"Camera '{name}' not found")

def export_cameras_to_csv():
    """Export camera list to CSV"""
    if not st.session_state.cameras:
        return None
    df = pd.DataFrame(st.session_state.cameras)
    return df.to_csv(index=False)

def import_cameras_from_csv(file):
    """Import cameras from CSV file"""
    try:
        df = pd.read_csv(file)
        new_cameras = df.to_dict('records')
        
        # Validate the data
        valid_cameras = []
        for cam in new_cameras:
            if 'name' in cam and 'address' in cam:
                valid_cameras.append({
                    'name': cam['name'],
                    'address': cam['address'],
                    'enabled': cam.get('enabled', True)
                })
        
        if valid_cameras:
            st.session_state.cameras.extend(valid_cameras)
            st.success(f"Successfully imported {len(valid_cameras)} cameras")
        else:
            st.error("No valid cameras found in the file")
    except Exception as e:
        st.error(f"Error importing cameras: {e}")

# ==============================================
# DETECTION FUNCTIONS (Originally from other files)
# ==============================================

def fire_detection_loop(video_placeholder, status_placeholder):
    """Mock fire detection function"""
    status_placeholder.info("Fire detection running (simulated)")
    for i in range(5):
        video_placeholder.image(f"https://picsum.photos/800/400?random={i}", use_column_width=True)
        st.session_state.telegram_status.append(f"Test alert {i+1} sent")
        asyncio.sleep(1)

def save_chat_data():
    """Mock function to save chat data"""
    pass

def occupancy_detection_loop(video_placeholder, stats_placeholder, hourly_placeholder, minute_placeholder):
    """Mock occupancy detection function"""
    stats_placeholder.info("Occupancy detection running (simulated)")
    for i in range(5):
        video_placeholder.image(f"https://picsum.photos/800/400?random={i+10}", use_column_width=True)
        
        # Update mock data
        st.session_state.occ_current_count = (i + 3) % 10
        st.session_state.occ_max_count = max(st.session_state.occ_max_count, st.session_state.occ_current_count)
        
        # Update hourly counts
        current_hour = datetime.now().hour
        if current_hour != st.session_state.occ_last_update_hour:
            st.session_state.occ_last_update_hour = current_hour
            st.session_state.occ_hourly_counts[current_hour] = st.session_state.occ_current_count
        
        # Update minute counts
        current_minute = datetime.now().minute
        absolute_minute = current_hour * 60 + current_minute
        st.session_state.occ_minute_counts[absolute_minute] = st.session_state.occ_current_count
        
        # Display stats
        stats_placeholder.write(f"""
        **Current Count:** {st.session_state.occ_current_count}  
        **Max Count Today:** {st.session_state.occ_max_count}
        """)
        
        # Plot hourly data
        fig, ax = plt.subplots()
        ax.plot(range(24), st.session_state.occ_hourly_counts, marker='o')
        ax.set_title("Hourly Occupancy")
        hourly_placeholder.pyplot(fig)
        plt.close(fig)
        
        asyncio.sleep(1)

def load_occupancy_data():
    """Mock function to load occupancy data"""
    return {}

def no_access_detection_loop(video_placeholder, table_placeholder, selected_cams):
    """Mock no-access detection function"""
    video_placeholder.info("No-access detection running (simulated)")
    for i in range(5):
        video_placeholder.image(f"https://picsum.photos/800/400?random={i+20}", use_column_width=True)
        
        # Mock table data
        mock_data = {
            "Timestamp": [datetime.now().strftime("%H:%M:%S")],
            "Camera": [selected_cams[0]['name'] if selected_cams else "Test Camera"],
            "Status": ["Alert" if i % 2 == 0 else "Clear"]
        }
        table_placeholder.table(pd.DataFrame(mock_data))
        asyncio.sleep(1)

def load_no_access_data():
    """Mock function to load no-access data"""
    return {}

# ==============================================
# MAIN APPLICATION
# ==============================================

def initialize_session_state():
    """Initialize all session state variables"""
    if 'cameras' not in st.session_state:
        st.session_state.cameras = []
    if 'confirm_remove' not in st.session_state:
        st.session_state.confirm_remove = None
    if 'processing_active' not in st.session_state:
        st.session_state.processing_active = False
    if 'fire_selected_cameras' not in st.session_state:
        st.session_state.fire_selected_cameras = []
    if 'occ_selected_cameras' not in st.session_state:
        st.session_state.occ_selected_cameras = []
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
    if 'no_access_selected_cameras' not in st.session_state:
        st.session_state.no_access_selected_cameras = []
    if 'no_access_detection_active' not in st.session_state:
        st.session_state.no_access_detection_active = False
    if 'tailgating_selected_cameras' not in st.session_state:
        st.session_state.tailgating_selected_cameras = []
    if 'tailgating_detection_active' not in st.session_state:
        st.session_state.tailgating_detection_active = False
    if 'chat_data' not in st.session_state:
        st.session_state.chat_data = [
            {"name": "Admin", "chat_id": "12345"},
            {"name": "Security", "chat_id": "67890"}
        ]

def show_camera_management_tab():
    """Display the camera management tab"""
    with st.expander("➕ Add New Camera", expanded=True):
        with st.form("add_camera_form"):
            col1, col2 = st.columns([1, 2])
            with col1:
                name = st.text_input("Camera Name")
            with col2:
                address = st.text_input("Camera Address (RTSP/HTTP)")
            
            if st.form_submit_button("Add Camera"):
                add_camera(name, address)
                st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Camera List")
    
    if not st.session_state.cameras:
        st.info("No cameras added yet.")
    else:
        # Export/Import buttons
        col1, col2 = st.columns(2)
        with col1:
            csv_data = export_cameras_to_csv()
            if csv_data:
                st.download_button(
                    label="📤 Export Cameras to CSV",
                    data=csv_data,
                    file_name="cameras_export.csv",
                    mime="text/csv"
                )
        with col2:
            uploaded_file = st.file_uploader(
                "📥 Import Cameras from CSV", 
                type=["csv"],
                accept_multiple_files=False,
                key="camera_import"
            )
            if uploaded_file:
                import_cameras_from_csv(uploaded_file)
                st.rerun()
        
        st.markdown("---")
        
        # Display cameras in an editable table
        for i, cam in enumerate(st.session_state.cameras):
            with st.container():
                cols = st.columns([3, 4, 2, 2])
                with cols[0]:
                    st.write(f"**{cam['name']}**")
                with cols[1]:
                    st.write(cam['address'])
                with cols[2]:
                    enabled = st.checkbox(
                        "Enabled", 
                        value=cam['enabled'],
                        key=f"enabled_{i}",
                        on_change=toggle_camera_status,
                        args=(cam['name'], not cam['enabled'])
                    )
                with cols[3]:
                    if st.button("❌ Remove", key=f"remove_{i}"):
                        st.session_state.confirm_remove = i
        
        # Confirmation dialog for removal
        if st.session_state.confirm_remove is not None:
            cam = st.session_state.cameras[st.session_state.confirm_remove]
            st.warning("🚨 Confirm Camera Removal")
            st.write(f"Are you sure you want to remove camera **{cam['name']}**?")
            st.write(f"Address: {cam['address']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, remove it"):
                    remove_camera(st.session_state.confirm_remove)
                    st.rerun()
            with col2:
                if st.button("❎ Cancel"):
                    st.session_state.confirm_remove = None
                    st.rerun()

def show_fire_detection_tab():
    """Display the fire detection tab"""
    st.header("🔥 Fire and Smoke Detection")
    
    with st.expander("🔔 Telegram Notification Settings"):
        st.subheader("Manage Recipients")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Add New Recipient")
            new_name = st.text_input("Recipient Name", key="new_recipient_name")
            new_chat_id = st.text_input("Recipient Chat ID", key="new_chat_id")
            if st.button("Add Recipient", key="add_recipient") and new_name and new_chat_id:
                st.session_state.chat_data.append({"name": new_name, "chat_id": new_chat_id})
                save_chat_data()
                st.success(f"Added {new_name} (Chat ID: {new_chat_id})")
                st.rerun()
        
        with col2:
            st.subheader("Current Recipients")
            for i, recipient in enumerate(st.session_state.chat_data):
                st.write(f"Name: {recipient['name']}, Chat ID: {recipient['chat_id']}")
                if st.button(f"Remove {recipient['name']}", key=f"remove_recipient_{i}"):
                    st.session_state.chat_data.pop(i)
                    save_chat_data()
                    st.rerun()
    
    if not st.session_state.cameras:
        st.warning("Please add cameras first in the Camera Management tab")
    else:
        st.subheader("📋 Available Cameras")
        selected = st.multiselect(
            "Select cameras to monitor for fire/smoke",
            [cam['name'] for cam in get_enabled_cameras()],
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
            if st.button("🔥 Start Fire Detection", 
                        disabled=not st.session_state.fire_selected_cameras,
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

def show_occupancy_detection_tab():
    """Display the occupancy detection tab"""
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
            [cam['name'] for cam in get_enabled_cameras()],
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
            if st.button("👥 Start Occupancy Tracking", 
                        disabled=not st.session_state.occ_selected_cameras,
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
            try:
                asyncio.run(occupancy_detection_loop(
                    video_placeholder, stats_placeholder,
                    hourly_chart_placeholder, minute_chart_placeholder
                ))
            except Exception as e:
                st.error(f"Occupancy detection failed: {e}")
                st.session_state.occ_detection_active = False

def show_tailgating_tab():
    """Display the tailgating detection tab"""
    st.header("🚪 Tailgating Detection")
    st.write("Detect unauthorized entry following authorized personnel.")
    
    # Historical data view
    view_history = st.checkbox("View Historical Data", key="view_tailgating_history")
    
    if view_history:
        st.subheader("Historical Tailgating Events")
        data = {}  # Mock data
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
            [cam['name'] for cam in get_enabled_cameras()],
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
            if st.button("🚪 Start Tailgating Detection", 
                        disabled=not st.session_state.tailgating_selected_cameras,
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
                selected_cams = [cam for cam in st.session_state.cameras 
                               if cam['name'] in st.session_state.tailgating_selected_cameras]
                asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cams))

def show_no_access_tab():
    """Display the no-access rooms detection tab"""
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
            [cam['name'] for cam in get_enabled_cameras()],
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
            if st.button("🔒 Start No-Access Detection", 
                        disabled=not st.session_state.no_access_selected_cameras,
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
                selected_cams = [cam for cam in st.session_state.cameras 
                               if cam['name'] in st.session_state.no_access_selected_cameras]
                asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cams))

def show_unattended_bags_tab():
    """Display the unattended bags detection tab"""
    st.header("👜 Unattended Bags Detection")
    st.write("Identify and alert about unattended bags in monitored areas.")
    if st.session_state.cameras:
        st.info("Unattended bags detection functionality would be implemented here")
    else:
        st.warning("Please add cameras first in the Camera Management tab")

def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
    # App UI
    st.set_page_config(page_title="📷 V.I.G.I.L", layout="wide")
    st.title("📷 V.I.G.I.L - Video Intelligence for General Inspection and Logging")
    
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
        show_camera_management_tab()
    
    with tab2:
        show_fire_detection_tab()
    
    with tab3:
        show_occupancy_detection_tab()
    
    with tab4:
        show_tailgating_tab()
    
    with tab5:
        show_unattended_bags_tab()
    
    with tab6:
        show_no_access_tab()

if __name__ == "__main__":
    main()
