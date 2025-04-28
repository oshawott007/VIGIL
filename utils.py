# camera_utils.py
import streamlit as st
import cv2
import numpy as np
import time
from pymongo import MongoClient

# MongoDB Atlas connection
MONGODB_URI = "mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Replace with your actual MongoDB Atlas URI
client = MongoClient(MONGODB_URI)
db = client['vigil']  # Database name
cameras_collection = db['cameras']  # Collection for cameras

def add_camera(name: str, address: str) -> None:
    """
    Add a new camera to MongoDB Atlas and update session state.
    
    Args:
        name (str): Name of the camera
        address (str): RTSP address or URL of the camera
    """
    if name and address:
        try:
            # Check if camera with same name or address already exists
            existing_camera = cameras_collection.find_one({"$or": [{"name": name}, {"address": address}]})
            if existing_camera:
                st.warning(f"⚠️ Camera with name '{name}' or address '{address}' already exists!")
                return
            
            # Create camera document
            new_camera = {
                "name": name,
                "address": address,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Insert into MongoDB
            cameras_collection.insert_one(new_camera)
            
            # Update session state
            st.session_state.cameras.append({"name": name, "address": address})
            st.success(f"📸 Camera '{name}' added successfully!")
            
        except Exception as e:
            st.warning(f"⚠️ Failed to add camera: {str(e)}")
    else:
        st.warning("⚠️ Please fill in both fields")

def remove_camera(index: int) -> None:
    """
    Remove a camera from MongoDB Atlas and update session state.
    
    Args:
        index (int): Index of the camera in the session state cameras list
    """
    if 0 <= index < len(st.session_state.cameras):
        try:
            removed = st.session_state.cameras[index]
            
            # Remove from MongoDB
            result = cameras_collection.delete_one({"name": removed['name'], "address": removed['address']})
            
            if result.deleted_count == 0:
                st.warning(f"⚠️ Camera '{removed['name']}' not found in database, removing from session state only.")
            
            # Remove from session state
            st.session_state.cameras.pop(index)
            
            # Remove from detection lists if present
            detection_lists = [
                'fire_selected_cameras',
                'occ_selected_cameras',
                'no_access_selected_cameras',
                'tailgating_selected_cameras'
            ]
            for detection_list in detection_lists:
                if removed['name'] in st.session_state.get(detection_list, []):
                    st.session_state[detection_list].remove(removed['name'])
            
            st.success(f"🗑️ Camera '{removed['name']}' removed!")
            
        except Exception as e:
            st.warning(f"⚠️ Failed to remove camera: {str(e)}")
    
    st.session_state.confirm_remove = None

def generate_mock_frame(camera_name: str) -> np.ndarray:
    """
    Generate a mock video frame with camera name overlay.
    
    Args:
        camera_name (str): Name of the camera to display on the frame
    
    Returns:
        np.ndarray: Generated mock frame
    """
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, f"Camera: {camera_name}", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, time.strftime("%Y-%m-%d %H:%M:%S"), (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.circle(frame, (np.random.randint(100, 540), np.random.randint(100, 380)), 
               30, (0, 0, 255), -1)
    return frame

def load_cameras() -> list:
    """
    Load all cameras from MongoDB Atlas into session state.
    
    Returns:
        list: List of camera dictionaries
    """
    try:
        cameras = list(cameras_collection.find())
        # Remove MongoDB's internal _id field and ensure format matches session state
        formatted_cameras = [
            {"name": cam["name"], "address": cam["address"]}
            for cam in cameras
        ]
        st.session_state.cameras = formatted_cameras
        return formatted_cameras
    except Exception as e:
        st.warning(f"⚠️ Failed to load cameras: {str(e)}")
        return []
