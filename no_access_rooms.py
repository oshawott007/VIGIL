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
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection setup
@st.cache_resource
def init_mongo_connection():
    try:
        # Replace with your MongoDB Atlas connection string
        client = MongoClient("mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        db = client["vigil"]
        return db.no_access_events
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

no_access_collection = init_mongo_connection()

@st.cache_resource
def load_model():
    try:
        model = YOLO('yolov8n.onnx')  # Using ONNX model
        logger.info("YOLO model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model. Error: {e}")
        return None

no_access_model = load_model()
if no_access_model is None:
    st.stop()

def save_no_access_event(timestamp: datetime, num_people: int, camera_name: str, snapshot: np.ndarray = None):
    """Save no-access event to MongoDB with optional image snapshot."""
    try:
        event = {
            'timestamp': timestamp,
            'date': timestamp.strftime("%Y-%m-%d"),
            'month': timestamp.strftime("%Y-%m"),
            'num_people': num_people,
            'camera_name': camera_name,
            'processed': False  # Flag for later processing if needed
        }
        
        # Optionally store image snapshot (compressed)
        if snapshot is not None:
            _, buffer = cv2.imencode('.jpg', snapshot)
            event['snapshot'] = buffer.tobytes()
        
        result = no_access_collection.insert_one(event)
        logger.info(f"Saved no-access event with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        logger.error(f"Failed to save no-access event: {e}")
        return None

def load_no_access_data(date_filter: str = None, month_filter: str = None) -> Dict[str, List[dict]]:
    """Load historical no-access data with optional date or month filtering."""
    try:
        query = {}
        if date_filter:
            query['date'] = date_filter
        elif month_filter:
            query['month'] = month_filter
        
        cursor = no_access_collection.find(query).sort('timestamp', -1)  # Newest first
        
        data = {}
        for doc in cursor:
            date = doc['date']
            if date not in data:
                data[date] = []
            entry = {
                'timestamp': doc['timestamp'],
                'num_people': doc['num_people'],
                'camera_name': doc['camera_name']
            }
            if 'snapshot' in doc:
                entry['has_snapshot'] = True
            data[date].append(entry)
        
        logger.info(f"Loaded {len(data)} days of no-access data")
        return data
    except Exception as e:
        logger.error(f"Failed to load no-access data: {e}")
        return {}

def get_available_dates() -> List[str]:
    """Get list of available dates with no-access events."""
    try:
        dates = no_access_collection.distinct('date')
        return sorted(dates, reverse=True)
    except Exception as e:
        logger.error(f"Failed to get available dates: {e}")
        return []

def get_available_months() -> List[str]:
    """Get list of available months with no-access events."""
    try:
        months = no_access_collection.distinct('month')
        return sorted(months, reverse=True)
    except Exception as e:
        logger.error(f"Failed to get available months: {e}")
        return []

async def no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras):
    """Main detection loop for no-access room monitoring."""
    confidence_threshold = 0.5
    human_class_id = 0  # COCO class ID for person
    delay_duration = 60  # 60-second delay after human detection
    last_detection_time = 0
    people_table = pd.DataFrame(columns=["Timestamp", "Number of People", "Camera"])
    last_timestamp = None

    # Initialize video captures
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
                    results = no_access_model(frame_rgb, conf=confidence_threshold)
                except Exception as e:
                    logger.error(f"Detection failed for {cam_name}: {e}")
                    continue

                human_detections = []
                for result in results:
                    for box in result.boxes:
                        if int(box.cls) == human_class_id and float(box.conf) >= confidence_threshold:
                            human_detections.append(box)

                # Annotate frame with detections
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

                # Add counters and camera name to frame
                cv2.putText(annotated_frame, f"Count: {len(human_detections)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(annotated_frame, f"Camera: {cam_name}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Display annotated frame
                try:
                    video_placeholder.image(annotated_frame, channels="RGB", caption=cam_name)
                except Exception as e:
                    logger.error(f"Failed to display frame for {cam_name}: {e}")
                    continue

                # Process detections
                if human_detections:
                    timestamp = datetime.now()
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    
                    if last_timestamp != timestamp_str:
                        # Save event to database with snapshot
                        save_no_access_event(
                            timestamp=timestamp,
                            num_people=len(human_detections),
                            camera_name=cam_name,
                            snapshot=frame  # Save original frame
                        )
                        
                        # Update table
                        new_entry = pd.DataFrame([[timestamp_str, len(human_detections), cam_name]],
                                              columns=["Timestamp", "Number of People", "Camera"])
                        people_table = pd.concat([people_table, new_entry], ignore_index=True)
                        
                        last_timestamp = timestamp_str
                        last_detection_time = current_time
                        logger.info(f"Human detected on {cam_name}, initiating 60-second pause")
                        table_placeholder.warning(f"Human detected on {cam_name}! Pausing for 60 seconds.")

                # Update detection table
                try:
                    if not people_table.empty:
                        table_placeholder.dataframe(people_table)
                    else:
                        table_placeholder.info("No human detections yet")
                except Exception as e:
                    logger.error(f"Table display failed for {cam_name}: {e}")

            await asyncio.sleep(0.03)  # ~30 FPS

    finally:
        # Clean up resources
        for cap in caps.values():
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Failed to release camera: {e}")
        cv2.destroyAllWindows()
        logger.info("Camera resources released")
