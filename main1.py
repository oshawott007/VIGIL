import pandas as pd
import streamlit as st
from datetime import datetime
import asyncio
import time  # Added for FPS control
from matplotlib import pyplot as plt
from utils import add_camera, remove_camera
from fire_detection import fire_detection_loop, save_chat_data
from occupancy_detection import occupancy_detection_loop, load_occupancy_data
from no_access_rooms import no_access_detection_loop, load_no_access_data


# Initialize session state
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
if 'occ_last_update_minute' not in st.session_state:
    st.session_state.occ_last_update_minute = -1
if 'no_access_selected_cameras' not in st.session_state:
    st.session_state.no_access_selected_cameras = []
if 'no_access_detection_active' not in st.session_state:
    st.session_state.no_access_detection_active = False

# Target FPS (7 frames per second)
TARGET_FPS = 4
FRAME_INTERVAL = 1.0 / TARGET_FPS  # Time between frames in seconds

# App UI
st.title("📷 V.I.G.I.L")

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
    with st.form("add_camera"):
        name = st.text_input("Camera Name")
        address = st.text_input("Camera Address")
        if st.form_submit_button("➕ Add Camera"):
            add_camera(name, address)

    st.header("📋 Camera List")
    if not st.session_state.cameras:
        st.info("No cameras added yet.")
    else:
        for i, cam in enumerate(st.session_state.cameras):
            col1, col2, col3 = st.columns([4, 4, 2])
            with col1:
                st.write(f"**{cam['name']}**")
            with col2:
                st.write(cam['address'])
            with col3:
                if st.button("❌ Remove", key=f"remove_{i}"):
                    st.session_state.confirm_remove = i

    if st.session_state.confirm_remove is not None:
        cam = st.session_state.cameras[st.session_state.confirm_remove]
        st.warning("🚨 Confirm Removal")
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
                status_placeholder.info("Fire detection active - monitoring selected cameras at 7 FPS...")
                last_frame_time = time.time()
                
                while st.session_state.fire_detection_active:
                    current_time = time.time()
                    elapsed = current_time - last_frame_time
                    
                    if elapsed >= FRAME_INTERVAL:
                        asyncio.run(fire_detection_loop(video_placeholder, status_placeholder))
                        last_frame_time = current_time
                    
                    # Small sleep to prevent CPU overuse
                    time.sleep(0.001)
        
        if st.session_state.telegram_status:
            status_placeholder.write("### Notification Status")
            for msg in st.session_state.telegram_status[-5:]:
                status_placeholder.write(msg)
        
        st.markdown("---")
        st.subheader("ℹ️ How to Find Your Telegram Chat ID")
        st.write("1. Start a chat with @userinfobot on Telegram")
        st.write("2. Send any message to the bot")
        st.write("3. The bot will reply with your chat ID")