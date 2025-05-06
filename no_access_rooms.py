

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
        model = YOLO('yolov8n.onnx')
        logger.info("YOLO model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model. Error: {e}")
        return None

no_access_model = load_model()

def save_no_access_event(camera_name: str):
    try:
        timestamp = datetime.now()
        event = {
            'camera_name': camera_name,
            'date': timestamp.strftime("%Y-%m-%d"),
            'time': timestamp.strftime("%H:%M:%S"),
            'timestamp': timestamp,
            'month': timestamp.strftime("%Y-%m")
        }
        result = no_access_collection.insert_one(event)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Failed to save event: {e}")
        return None

def load_no_access_data(date_filter: str = None, month_filter: str = None) -> Dict[str, List[dict]]:
    try:
        query = {}
        if date_filter:
            query['date'] = date_filter
        elif month_filter:
            query['month'] = month_filter
        
        cursor = no_access_collection.find(query).sort('timestamp', -1)
        
        data = {}
        for doc in cursor:
            date = doc['date']
            if date not in data:
                data[date] = []
            entry = {
                'timestamp': doc['timestamp'],
                'camera_name': doc['camera_name'],
                'time': doc['time']
            }
            data[date].append(entry)
        
        return data
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {}

def get_available_dates() -> List[str]:
    try:
        dates = no_access_collection.distinct('date')
        return sorted(dates, reverse=True)
    except Exception as e:
        logger.error(f"Failed to get dates: {e}")
        return []

async def no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras):
    confidence_threshold = 0.5
    human_class_id = 0
    cooldown_duration = 300
    last_detection_time = 0
    detections_table = pd.DataFrame(columns=["Camera", "Date", "Time"])

    caps = {}
    for cam in selected_cameras:
        try:
            cap = cv2.VideoCapture(cam['address'])
            if cap.isOpened():
                caps[cam['name']] = cap
        except Exception as e:
            logger.error(f"Camera {cam['name']} error: {e}")

    if not caps:
        video_placeholder.error("No cameras available")
        return

    try:
        while st.session_state.no_access_detection_active and caps:
            current_time = time.time()
            
            if current_time - last_detection_time < cooldown_duration:
                remaining_time = int(cooldown_duration - (current_time - last_detection_time))
                table_placeholder.warning(f"Cooldown active - {remaining_time}s remaining")
                await asyncio.sleep(1)
                continue

            for cam_name, cap in caps.items():
                ret, frame = cap.read()
                if not ret:
                    continue

                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = no_access_model(frame_rgb, conf=confidence_threshold)
                    
                    human_detections = [
                        box for result in results 
                        for box in result.boxes 
                        if int(box.cls) == human_class_id and float(box.conf) >= confidence_threshold
                    ]

                    annotated_frame = frame_rgb.copy()
                    for box in human_detections:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f"Person {float(box.conf):.2f}", 
                                   (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    cv2.putText(annotated_frame, f"Count: {len(human_detections)}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(annotated_frame, f"Camera: {cam_name}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    video_placeholder.image(annotated_frame, channels="RGB", caption=cam_name)

                    if human_detections:
                        save_no_access_event(cam_name)
                        timestamp = datetime.now()
                        new_entry = pd.DataFrame([[cam_name, timestamp.strftime("%Y-%m-%d"), 
                                                 timestamp.strftime("%H:%M:%S")]],
                                              columns=["Camera", "Date", "Time"])
                        detections_table = pd.concat([detections_table, new_entry], ignore_index=True)
                        last_detection_time = current_time
                        table_placeholder.warning(f"Human detected! Cooldown for {cooldown_duration}s")

                    if not detections_table.empty:
                        table_placeholder.dataframe(detections_table)

                except Exception as e:
                    logger.error(f"Processing error: {e}")

            await asyncio.sleep(0.03)

    finally:
        for cap in caps.values():
            cap.release()
        cv2.destroyAllWindows()
