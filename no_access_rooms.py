import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime
import pandas as pd
import numpy as np
import time
import logging
import asyncio
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
@st.cache_resource
def init_mongo():
    try:
        client = MongoClient('mongodb://localhost:27017/')  # Update with your MongoDB URI if needed
        db = client['cctv_analysis']
        collection = db['no_access_events']
        logger.info("MongoDB connection established")
        return collection
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

no_access_collection = init_mongo()
if no_access_collection is None:
    st.stop()

# Load human detection model
# @st.cache_resource
# def load_model():
#     try:
#         model = YOLO('yolov8n.pt')  # Replace with your custom human detection model path
#         logger.info("Human detection model loaded successfully")
#         return model
#     except Exception as e:
#         logger.error(f"Failed to load human detection model: {e}")
#         st.error(f"Failed to load human detection model: {e}")
#         return None

# no_access_model = load_model()


@st.cache_resource
def load_model():
    try:
        model = YOLO('yolov8n.onnx')
        return model
    except Exception as e:
        st.error(f"Failed to load model. Error: {e}")
        return None

model = load_model()
if model is None:
    st.stop()

# Function to save no-access event to MongoDB
def save_no_access_event(timestamp, num_people, camera_name):
    try:
        event = {
            'timestamp': timestamp,
            'date': timestamp.strftime("%Y-%m-%d"),
            'num_people': num_people,
            'camera_name': camera_name
        }
        no_access_collection.insert_one(event)
        logger.info(f"Saved no-access event: {event}")
    except Exception as e:
        logger.error(f"Failed to save no-access event: {e}")

# Function to load historical no-access data
def load_no_access_data():
    try:
        data = {}
        cursor = no_access_collection.find()
        for doc in cursor:
            date = doc['date']
            if date not in data:
                data[date] = []
            data[date].append({
                'timestamp': doc['timestamp'],
                'num_people': doc['num_people'],
                'camera_name': doc['camera_name']
            })
        return data
    except Exception as e:
        logger.error(f"Failed to load no-access data: {e}")
        return {}

# Async function for no-access room detection loop
async def no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras):
    confidence_threshold = 0.5
    human_class_id = 0  # COCO class ID for person
    delay_duration = 60  # 60-second delay after human detection
    last_detection_time = 0
    people_table = pd.DataFrame(columns=["Timestamp", "Number of People", "Camera"])
    last_timestamp = None

    caps = {}
    for cam in selected_cameras:
        try:
            cap = cv2.VideoCapture(cam['address'])
            if not cap.isOpened():
                logger.error(f"Could not open camera {cam['name']}")
                continue
            caps[cam['name']] = cap
        except Exception as e:
            logger.error(f"Failed to initialize camera {cam['name']}: {e}")
            continue

    if not caps:
        video_placeholder.error("No cameras available for no-access room detection")
        return

    try:
        while st.session_state.no_access_detection_active and caps:
            current_time = time.time()
            if current_time - last_detection_time < delay_duration:
                await asyncio.sleep(0.1)
                continue

            for cam_name, cap in caps.items():
                ret, frame = cap.read()
                if not ret:
                    logger.error(f"Failed to capture frame from {cam_name}")
                    continue

                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                except Exception as e:
                    logger.error(f"Frame conversion failed for {cam_name}: {e}")
                    continue

                try:
                    results = no_access_model.predict(frame_rgb, conf=confidence_threshold)
                except Exception as e:
                    logger.error(f"Detection failed for {cam_name}: {e}")
                    continue

                human_detections = []
                for result in results:
                    for box in result.boxes:
                        if int(box.cls) == human_class_id:
                            human_detections.append(box)

                annotated_frame = frame_rgb.copy()
                for box in human_detections:
                    try:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f"Person {conf:.2f}", (x1, y1-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    except Exception as e:
                        logger.warning(f"Failed to draw box for {cam_name}: {e}")
                        continue

                cv2.putText(annotated_frame, f"Count: {len(human_detections)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(annotated_frame, f"Camera: {cam_name}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                try:
                    video_placeholder.image(annotated_frame, channels="RGB", caption=cam_name)
                except Exception as e:
                    logger.error(f"Failed to display frame for {cam_name}: {e}")
                    continue

                if len(human_detections) > 0:
                    timestamp = datetime.now()
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if last_timestamp != timestamp_str:
                        save_no_access_event(timestamp, len(human_detections), cam_name)
                        new_entry = pd.DataFrame([[timestamp_str, len(human_detections), cam_name]],
                                                columns=["Timestamp", "Number of People", "Camera"])
                        people_table = pd.concat([people_table, new_entry], ignore_index=True)
                        last_timestamp = timestamp_str
                        last_detection_time = current_time
                        logger.info(f"Human detected on {cam_name}, initiating 60-second pause")
                        table_placeholder.warning(f"Human detected on {cam_name}! Pausing for 60 seconds.")

                try:
                    if not people_table.empty:
                        table_placeholder.dataframe(people_table)
                    else:
                        table_placeholder.info("No human detections yet")
                except Exception as e:
                    logger.error(f"Table display failed for {cam_name}: {e}")

            await asyncio.sleep(0.03)  # ~30 FPS

    finally:
        for cap in caps.values():
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Failed to release camera: {e}")
        cv2.destroyAllWindows()
        logger.info("Camera resources released")
