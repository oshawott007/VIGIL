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
from config import BOT_TOKEN, CHAT_DATA_FILE


from torch.serialization import add_safe_globals
from ultralytics.nn.tasks import DetectionModel

# Option 1: Using context manager
with add_safe_globals([DetectionModel]):
    model = YOLO('best.pt')  # Your model path

# Option 2: Permanently allow (add at startup)
add_safe_globals([DetectionModel])
model = YOLO('best.pt')
classnames = ['fire', 'smoke']
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
                    # File is empty, return default data
                    return [{"chat_id": "1091767594", "name": "Default User"}]
        except json.JSONDecodeError:
            # File contains invalid JSON, return default data
            st.warning(f"Invalid JSON in {CHAT_DATA_FILE}. Initializing with default data.")
            return [{"chat_id": "1091767594", "name": "Default User"}]
    else:
        # File doesn't exist, return default data
        return [{"chat_id": "1091767594", "name": "Default User"}]

chat_data = load_chat_data()
# Save default data if file was empty or invalid
if not os.path.exists(CHAT_DATA_FILE) or os.path.getsize(CHAT_DATA_FILE) == 0:
    with open(CHAT_DATA_FILE, 'w') as f:
        json.dump(chat_data, f)

# Load the YOLO model for fire detection
# try:
#     fire_model = YOLO('best.pt')
#     classnames = ['fire', 'smoke']
# except Exception as e:
#     st.error(f"Failed to load fire detection YOLO model: {e}")
#     fire_model = None

async def send_snapshot(frame, chat_id, name):
    """Send a snapshot to Telegram"""
    try:
        image_path = 'snapshot.png'
        cv2.imwrite(image_path, frame)
        with open(image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, 
                               caption=f"Fire/Smoke detected! Alert from security system.")
        return f"Alert sent to {name} (Chat ID: {chat_id})"
    except TelegramError as e:
        return f"Error sending to {name} (Chat ID: {chat_id}): {e}"

def save_chat_data():
    """Save chat data to file"""
    with open(CHAT_DATA_FILE, 'w') as f:
        json.dump(chat_data, f)

def process_fire_detection(frame, camera_name):
    """Process frame for fire detection"""
    if fire_model is None:
        return frame, False
    
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

    return frame, fire_or_smoke_detected

async def fire_detection_loop(video_placeholder, status_placeholder):
    """Main fire detection loop"""
    last_sent = 0
    
    # Initialize video captures for selected cameras
    caps = {}
    for cam_name in st.session_state.fire_selected_cameras:
        cam_address = next((cam['address'] for cam in st.session_state.cameras 
                          if cam['name'] == cam_name), None)
        if cam_address:
            cap = cv2.VideoCapture(cam_address)
            if cap.isOpened():
                caps[cam_name] = cap
            else:
                status_placeholder.error(f"Failed to open camera: {cam_name}")
    
    if not caps:
        status_placeholder.error("No valid cameras available")
        return
    
    while st.session_state.fire_detection_active:
        current_time = time.time()
        frames = {}
        fire_detected = False
        
        for cam_name, cap in caps.items():
            ret, frame = cap.read()
            if ret:
                frame, detected = process_fire_detection(frame, cam_name)
                frames[cam_name] = frame
                if detected:
                    fire_detected = True
        
        if frames:
            cols = st.columns(2)
            for i, (cam_name, frame) in enumerate(frames.items()):
                with cols[i % 2]:
                    video_placeholder.image(frame, channels="BGR", 
                                          caption=f"{cam_name}", 
                                          use_container_width=True)
        
        if fire_detected and (current_time - last_sent) > 10:
            for cam_name, frame in frames.items():
                if fire_detected:
                    for recipient in chat_data:
                        status = await send_snapshot(frame, recipient["chat_id"], recipient["name"])
                        st.session_state.telegram_status.append(status)
                    last_sent = current_time
        
        await asyncio.sleep(0.1)
    
    for cap in caps.values():
        cap.release()
