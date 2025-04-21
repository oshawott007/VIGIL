import streamlit as st
from utils import init_session_state

def show_camera_management():
    init_session_state()
    
    # Add Camera Form
    with st.form("add_camera"):
        name = st.text_input("Camera Name")
        address = st.text_input("Camera Address")
        if st.form_submit_button("➕ Add Camera"):
            add_camera(name, address)

    # Display Cameras
    st.header("📋 Camera List")
    if not st.session_state.cameras:
        st.info("No cameras added yet.")
    else:
        display_camera_list()

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

def display_camera_list():
    """Display the list of cameras with remove buttons"""
    for i, cam in enumerate(st.session_state.cameras):
        col1, col2, col3 = st.columns([4, 4, 2])
        with col1:
            st.write(f"**{cam['name']}**")
        with col2:
            st.write(cam['address'])
        with col3:
            if st.button("❌ Remove", key=f"remove_{i}"):
                st.session_state.confirm_remove = i
    
    show_remove_confirmation()

def show_remove_confirmation():
    """Show confirmation dialog for camera removal"""
    if st.session_state.get('confirm_remove') is not None:
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

def remove_camera(index):
    """Remove a camera by index"""
    if 0 <= index < len(st.session_state.cameras):
        removed = st.session_state.cameras.pop(index)
        if removed['name'] in st.session_state.selected_cameras:
            st.session_state.selected_cameras.remove(removed['name'])
        st.success(f"🗑️ Camera '{removed['name']}' removed!")
    st.session_state.confirm_remove = None