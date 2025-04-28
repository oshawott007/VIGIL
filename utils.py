# utils.py
import streamlit as st
from db import add_camera_to_db, get_cameras_from_db, remove_camera_from_db

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
