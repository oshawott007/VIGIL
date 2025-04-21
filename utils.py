# camera_utils.py
import streamlit as st
import cv2
import numpy as np
import time

def add_camera(name, address):
    """Add a new camera to the list"""
    if name and address:
        if any(cam['name'] == name for cam in st.session_state.cameras):
            st.warning(f"⚠️ Camera with name '{name}' already exists!")
            return
        new_camera = {"name": name, "address": address}
        st.session_state.cameras.append(new_camera)
        st.success(f"📸 Camera '{name}' added successfully!")
    else:
        st.warning("⚠️ Please fill in both fields")

def remove_camera(index):
    """Remove a camera by index"""
    if 0 <= index < len(st.session_state.cameras):
        removed = st.session_state.cameras.pop(index)
        if removed['name'] in st.session_state.fire_selected_cameras:
            st.session_state.fire_selected_cameras.remove(removed['name'])
        if removed['name'] in st.session_state.occ_selected_cameras:
            st.session_state.occ_selected_cameras.remove(removed['name'])
        st.success(f"🗑️ Camera '{removed['name']}' removed!")
    st.session_state.confirm_remove = None

def generate_mock_frame(camera_name):
    """Generate a mock video frame with camera name overlay"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, f"Camera: {camera_name}", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, time.strftime("%Y-%m-%d %H:%M:%S"), (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.circle(frame, (np.random.randint(100, 540), np.random.randint(100, 380)), 
               30, (0, 0, 255), -1)
    return frame