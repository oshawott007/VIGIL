
# fire_detection.py
import time
import streamlit as st
import cv2
import numpy as np
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from ultralytics import YOLO
import cvzone
import math
import json
import os
import logging
from config import BOT_TOKEN, CHAT_DATA_FILE

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the bot
bot = Bot(token=BOT_TOKEN)

# Load chat data
def load_chat_data():
    """Load chat data from JSON file, handling empty or invalid files"""
    if os.path.exists(CHAT_DATA_FILE):
        try:
            with open(CHAT_DATA_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    logger.warning(f"Empty chat data file: {CHAT_DATA_FILE}")
                    return [{"chat_id": "1091767594", "name": "Default User"}]
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {CHAT_DATA_FILE}: {e}")
            st.warning(f"Invalid JSON in {CHAT_DATA_FILE}. Initializing with default data.")
            return [{"chat_id": "1091767594", "name": "Default User"}]
    else:
        logger.info(f"Chat data file not found: {CHAT_DATA_FILE}")
        return [{"chat_id": "1091767594", "name": "Default User"}]

chat_data = load_chat_data()
# Save default data if file was empty or invalid
if not os.path.exists(CHAT_DATA_FILE) or os.path.getsize(CHAT_DATA_FILE) == 0:
    with open(CHAT_DATA_FILE, 'w') as f:
        json.dump(chat_data, f)

# Load the YOLO model for fire detection
try:
    fire_model = YOLO('best.onnx')
    classnames = ['fire', 'smoke']
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load fire detection YOLO model: {e}")
    st.error(f"Failed to load fire detection YOLO model: {e}")
    fire_model = None

async def send_snapshot(frame, chat_id, name):
    """Send a snapshot to Telegram"""
    try:
        if not isinstance(frame, np.ndarray):
            logger.error(f"Invalid frame type for snapshot: {type(frame)}")
            return f"Error sending to {name} (Chat ID: {chat_id}): Invalid frame"
        
        image_path = 'snapshot.png'
        cv2.imwrite(image_path, frame)
        with open(image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, 
                               caption=f"Fire/Smoke detected! Alert from security system.")
        logger.info(f"Snapshot sent to {name} (Chat ID: {chat_id})")
        return f"Alert sent to {name} (Chat ID: {chat_id})"
    except TelegramError as e:
        logger.error(f"Telegram error for {name} (Chat ID: {chat_id}): {e}")
        return f"Error sending to {name} (Chat ID: {chat_id}): {e}"

def save_chat_data():
    """Save chat data to file"""
    try:
        with open(CHAT_DATA_FILE, 'w') as f:
            json.dump(chat_data, f)
        logger.info("Chat data saved successfully")
    except Exception as e:
        logger.error(f"Failed to save chat data: {e}")

def process_fire_detection(frame, camera_name):
    """Process frame for fire detection"""
    if fire_model is None:
        logger.warning(f"No YOLO model available for {camera_name}")
        return frame, False
    
    if not isinstance(frame, np.ndarray) or frame.size == 0:
        logger.error(f"Invalid frame for {camera_name}: {frame}")
        return frame, False

    try:
        frame = cv2.resize(frame, (640, 480))
        result = fire_model(frame, stream=True)
        fire_or_smoke_detected = False

        for info in result:
            boxes = info.boxes
            for box in boxes:
                confidence = box.conf[0]
                confidence = math.ceil(confidence * 100)
                Class = int(box.cls[0])
                if confidence > 80:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 5)
                    cvzone.putTextRect(frame, f'{classnames[Class]} {confidence}%', 
                                     [x1 + 8, y1 + 100], scale=1.5, thickness=2)
                    fire_or_smoke_detected = True
                    cv2.putText(frame, "ALERT!", (50, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        logger.debug(f"Processed frame for {camera_name}, fire/smoke: {fire_or_smoke_detected}")
        return frame, fire_or_smoke_detected
    except Exception as e:
        logger.error(f"Error processing frame for {camera_name}: {e}")
        return frame, False

# async def fire_detection_loop(video_placeholders, status_placeholder):
#     """Main fire detection loop"""
#     last_sent = 0
#     logger.info("Starting fire detection loop")
    
#     # Initialize video captures for selected cameras
#     caps = {}
#     for cam_name in st.session_state.fire_selected_cameras:
#         cam_address = next((cam['address'] for cam in st.session_state.cameras 
#                           if cam['name'] == cam_name), None)
#         if cam_address:
#             logger.info(f"Opening camera: {cam_name} at {cam_address}")
#             cap = cv2.VideoCapture(cam_address)
#             if cap.isOpened():
#                 caps[cam_name] = cap
#                 # Initialize placeholder for this camera
#                 if cam_name not in video_placeholders:
#                     video_placeholders[cam_name] = st.empty()
#             else:
#                 logger.error(f"Failed to open camera: {cam_name} at {cam_address}")
#                 status_placeholder.error(f"Failed to open camera: {cam_name}")
    
#     if not caps:
#         logger.error("No valid cameras available")
#         status_placeholder.error("No valid cameras available")
#         return
    
#     while st.session_state.fire_detection_active:
#         current_time = time.time()
#         frames = {}
#         fire_detected = False
        
#         for cam_name, cap in caps.items():
#             ret, frame = cap.read()
#             if ret and isinstance(frame, np.ndarray) and frame.size > 0:
#                 frame, detected = process_fire_detection(frame, cam_name)
#                 frames[cam_name] = frame
#                 if detected:
#                     fire_detected = True
#             else:
#                 logger.warning(f"Failed to read frame from {cam_name}")
#                 status_placeholder.warning(f"Failed to read frame from {cam_name}")
        
#         # Display frames
#         for cam_name, frame in frames.items():
#             try:
#                 video_placeholders[cam_name].image(
#                     frame,
#                     channels="BGR",
#                     caption=f"{cam_name}",
#                     use_container_width=True
#                 )
#                 logger.debug(f"Displayed frame for {cam_name}")
#             except Exception as e:
#                 logger.error(f"Error displaying frame for {cam_name}: {e}")
#                 status_placeholder.error(f"Error displaying frame for {cam_name}: {e}")
        
#         # Send Telegram alerts if fire/smoke detected
#         if fire_detected and (current_time - last_sent) > 10:
#             for cam_name, frame in frames.items():
#                 if fire_detected:
#                     for recipient in chat_data:
#                         status = await send_snapshot(frame, recipient["chat_id"], recipient["name"])
#                         st.session_state.telegram_status.append(status)
#                         logger.info(status)
#                     last_sent = current_time
        
#         await asyncio.sleep(0.1)  # ~10 FPS to reduce load
    
#     # Cleanup
#     for cam_name, cap in caps.items():
#         cap.release()
#         logger.info(f"Released camera: {cam_name}")
    
#     logger.info("Fire detection loop ended")


async def fire_detection_loop(video_placeholders, status_placeholder):
    """Main fire detection loop"""
    last_sent = 0
    logger.info("Starting fire detection loop")
    
    # Initialize video captures for selected cameras
    caps = {}
    if not hasattr(st.session_state, 'fire_selected_cameras'):
        status_placeholder.error("No cameras selected for fire detection")
        return
    
    # Ensure video_placeholders is a dictionary
    if not isinstance(video_placeholders, dict):
        video_placeholders = {}
    
    for cam_name in st.session_state.fire_selected_cameras:
        cam_address = next((cam['address'] for cam in st.session_state.cameras 
                          if cam['name'] == cam_name), None)
        if cam_address:
            logger.info(f"Opening camera: {cam_name} at {cam_address}")
            cap = cv2.VideoCapture(cam_address)
            if cap.isOpened():
                caps[cam_name] = cap
                # Initialize placeholder for this camera if it doesn't exist
                if cam_name not in video_placeholders:
                    video_placeholders[cam_name] = st.empty()
            else:
                logger.error(f"Failed to open camera: {cam_name} at {cam_address}")
                status_placeholder.error(f"Failed to open camera: {cam_name}")
    
    if not caps:
        logger.error("No valid cameras available")
        status_placeholder.error("No valid cameras available")
        return
    
    while st.session_state.fire_detection_active:
        current_time = time.time()
        frames = {}
        fire_detected = False
        
        for cam_name, cap in caps.items():
            ret, frame = cap.read()
            if ret and isinstance(frame, np.ndarray) and frame.size > 0:
                frame, detected = process_fire_detection(frame, cam_name)
                frames[cam_name] = frame
                if detected:
                    fire_detected = True
            else:
                logger.warning(f"Failed to read frame from {cam_name}")
                status_placeholder.warning(f"Failed to read frame from {cam_name}")
        
        # Display frames - only for cameras that have frames
        for cam_name in frames:
            try:
                if cam_name in video_placeholders:  # Check if placeholder exists
                    video_placeholders[cam_name].image(
                        frames[cam_name],
                        channels="BGR",
                        caption=f"{cam_name}",
                        # use_container_width=True
                    )
                    # logger.debug(f"Displayed frame for {cam_name}")
            except Exception as e:
                logger.error(f"Error displaying frame for {cam_name}: {e}")
                status_placeholder.error(f"Error displaying frame for {cam_name}: {e}")
        
        # Send Telegram alerts if fire/smoke detected
        if fire_detected and (current_time - last_sent) > 10:
            for cam_name, frame in frames.items():
                if fire_detected:
                    for recipient in chat_data:
                        status = await send_snapshot(frame, recipient["chat_id"], recipient["name"])
                        st.session_state.telegram_status.append(status)
                        logger.info(status)
                    last_sent = current_time
        
        await asyncio.sleep(0.1)  # ~10 FPS to reduce load
    
    # Cleanup
    for cam_name, cap in caps.items():
        cap.release()
        logger.info(f"Released camera: {cam_name}")
    
    logger.info("Fire detection loop ended")
