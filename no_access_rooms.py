# import streamlit as st
# import cv2
# from ultralytics import YOLO
# from datetime import datetime, timedelta
# import pandas as pd
# import numpy as np
# import time
# import logging
# import asyncio
# import json
# import os
# from typing import Dict, List

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # JSON file for data storage
# DATA_FILE = "no_access_events.json"

# def init_json_storage():
#     try:
#         # Sample data for testing historical view
#         sample_data = [
#             {
#                 'camera_name': "Entrance Camera",
#                 'date': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
#                 'time': "10:15:32",
#                 'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
#                 'month': (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
#             },
#             {
#                 'camera_name': "Backdoor Camera",
#                 'date': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
#                 'time': "14:22:45",
#                 'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
#                 'month': (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
#             },
#             {
#                 'camera_name': "Warehouse Camera",
#                 'date': datetime.now().strftime("%Y-%m-%d"),
#                 'time': "09:05:12",
#                 'timestamp': datetime.now().isoformat(),
#                 'month': datetime.now().strftime("%Y-%m")
#             }
#         ]

#         if not os.path.exists(DATA_FILE):
#             with open(DATA_FILE, 'w') as f:
#                 json.dump(sample_data, f)
#             logger.info("Created new data file with sample records")
#         else:
#             # If file exists but is empty, add sample data
#             with open(DATA_FILE, 'r') as f:
#                 try:
#                     existing_data = json.load(f)
#                     if not existing_data:
#                         with open(DATA_FILE, 'w') as f:
#                             json.dump(sample_data, f)
#                         logger.info("Added sample records to empty data file")
#                 except json.JSONDecodeError:
#                     with open(DATA_FILE, 'w') as f:
#                         json.dump(sample_data, f)
#                     logger.info("Created new data file (invalid JSON)")
#     except Exception as e:
#         logger.error(f"Failed to initialize JSON storage: {e}")

# def save_no_access_event(camera_name: str):
#     try:
#         timestamp = datetime.now()
#         event = {
#             'camera_name': camera_name,
#             'date': timestamp.strftime("%Y-%m-%d"),
#             'time': timestamp.strftime("%H:%M:%S"),
#             'timestamp': timestamp.isoformat(),
#             'month': timestamp.strftime("%Y-%m")
#         }
        
#         with open(DATA_FILE, 'r') as f:
#             data = json.load(f)
        
#         data.append(event)
        
#         with open(DATA_FILE, 'w') as f:
#             json.dump(data, f)
            
#         return True
#     except Exception as e:
#         logger.error(f"Failed to save event: {e}")
#         return None

# def load_no_access_data(date_filter: str = None, month_filter: str = None) -> Dict[str, List[dict]]:
#     try:
#         with open(DATA_FILE, 'r') as f:
#             data = json.load(f)
        
#         filtered_data = []
#         for event in data:
#             if date_filter and event['date'] == date_filter:
#                 filtered_data.append(event)
#             elif month_filter and event['month'] == month_filter:
#                 filtered_data.append(event)
#             elif not date_filter and not month_filter:
#                 filtered_data.append(event)
        
#         organized_data = {}
#         for event in filtered_data:
#             date = event['date']
#             if date not in organized_data:
#                 organized_data[date] = []
#             entry = {
#                 'timestamp': datetime.fromisoformat(event['timestamp']),
#                 'camera_name': event['camera_name'],
#                 'time': event['time']
#             }
#             organized_data[date].append(entry)
        
#         for date in organized_data:
#             organized_data[date].sort(key=lambda x: x['timestamp'], reverse=True)
        
#         return organized_data
#     except Exception as e:
#         logger.error(f"Failed to load data: {e}")
#         return {}

# def get_available_dates() -> List[str]:
#     try:
#         with open(DATA_FILE, 'r') as f:
#             data = json.load(f)
        
#         dates = list(set(event['date'] for event in data))
#         return sorted(dates, reverse=True)
#     except Exception as e:
#         logger.error(f"Failed to get dates: {e}")
#         return []

# @st.cache_resource
# def load_model():
#     try:
#         model = YOLO('yolov8n.onnx')
#         logger.info("YOLO model loaded successfully")
#         return model
#     except Exception as e:
#         logger.error(f"Failed to load model. Error: {e}")
#         return None

# no_access_model = load_model()
# init_json_storage()

# async def no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras):
#     confidence_threshold = 0.5
#     human_class_id = 0
#     cooldown_duration = 300
#     last_detection_time = 0
#     detections_table = pd.DataFrame(columns=["Camera", "Date", "Time"])

#     caps = {}
#     for cam in selected_cameras:
#         try:
#             cap = cv2.VideoCapture(cam['address'])
#             if cap.isOpened():
#                 caps[cam['name']] = cap
#         except Exception as e:
#             logger.error(f"Camera {cam['name']} error: {e}")

#     if not caps:
#         video_placeholder.error("No cameras available")
#         return

#     try:
#         while st.session_state.no_access_detection_active and caps:
#             current_time = time.time()
            
#             if current_time - last_detection_time < cooldown_duration:
#                 remaining_time = int(cooldown_duration - (current_time - last_detection_time))
#                 table_placeholder.warning(f"Cooldown active - {remaining_time}s remaining")
#                 await asyncio.sleep(1)
#                 continue

#             for cam_name, cap in caps.items():
#                 ret, frame = cap.read()
#                 if not ret:
#                     continue

#                 try:
#                     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                     results = no_access_model(frame_rgb, conf=confidence_threshold)
                    
#                     human_detections = [
#                         box for result in results 
#                         for box in result.boxes 
#                         if int(box.cls) == human_class_id and float(box.conf) >= confidence_threshold
#                     ]

#                     annotated_frame = frame_rgb.copy()
#                     for box in human_detections:
#                         x1, y1, x2, y2 = map(int, box.xyxy[0])
#                         cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#                         cv2.putText(annotated_frame, f"Person {float(box.conf):.2f}", 
#                                    (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

#                     cv2.putText(annotated_frame, f"Count: {len(human_detections)}", (10, 30),
#                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#                     cv2.putText(annotated_frame, f"Camera: {cam_name}", (10, 60),
#                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

#                     video_placeholder.image(annotated_frame, channels="RGB", caption=cam_name)

#                     if human_detections:
#                         save_no_access_event(cam_name)
#                         timestamp = datetime.now()
#                         new_entry = pd.DataFrame([[cam_name, timestamp.strftime("%Y-%m-%d"), 
#                                                  timestamp.strftime("%H:%M:%S")]],
#                                               columns=["Camera", "Date", "Time"])
#                         detections_table = pd.concat([detections_table, new_entry], ignore_index=True)
#                         last_detection_time = current_time
#                         table_placeholder.warning(f"Human detected! Cooldown for {cooldown_duration}s")

#                     if not detections_table.empty:
#                         table_placeholder.dataframe(detections_table)

#                 except Exception as e:
#                     logger.error(f"Processing error: {e}")

#             await asyncio.sleep(0.03)

#     finally:
#         for cap in caps.values():
#             cap.release()
#         cv2.destroyAllWindows()

# def main():
#     st.title("Restricted Area Monitoring System")
    
#     # Historical Data View Section
#     st.sidebar.header("Historical Data")
#     view_option = st.sidebar.radio("View by", ["All Data", "Date", "Month"])
    
#     if view_option == "Date":
#         available_dates = get_available_dates()
#         selected_date = st.sidebar.selectbox("Select Date", available_dates)
#         historical_data = load_no_access_data(date_filter=selected_date)
#     elif view_option == "Month":
#         available_months = sorted(list(set(d[:7] for d in get_available_dates())), reverse=True)
#         selected_month = st.sidebar.selectbox("Select Month", available_months)
#         historical_data = load_no_access_data(month_filter=selected_month)
#     else:
#         historical_data = load_no_access_data()
    
#     if historical_data:
#         st.subheader("Detection History")
#         for date, events in historical_data.items():
#             st.markdown(f"**{date}**")
#             df = pd.DataFrame(events)
#             df = df[['time', 'camera_name']]  # Don't show timestamp column
#             st.table(df)
#     else:
#         st.info("No historical data available")

#     # Live Monitoring Section
#     st.sidebar.header("Live Monitoring")
#     cameras = [
#         {"name": "Camera 1", "address": 0},
#         {"name": "Camera 2", "address": "http://example.com/stream"}
#     ]
    
#     selected_camera_names = st.sidebar.multiselect(
#         "Select Cameras",
#         [cam["name"] for cam in cameras],
#         default=[cameras[0]["name"]]
#     )
    
#     selected_cameras = [cam for cam in cameras if cam["name"] in selected_camera_names]
    
#     if st.sidebar.button("Start Monitoring"):
#         st.session_state.no_access_detection_active = True
#         video_placeholder = st.empty()
#         table_placeholder = st.empty()
#         asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras))
    
#     if st.sidebar.button("Stop Monitoring"):
#         if 'no_access_detection_active' in st.session_state:
#             st.session_state.no_access_detection_active = False
#         st.experimental_rerun()

# if __name__ == "__main__":
#     main()









import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime, timedelta
import pandas as pd
import time
import logging
import asyncio
import json
import os
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JSON file for data storage
DATA_FILE = "detection_events.json"

def initialize_data_file():
    """Initialize the JSON data file with sample data if it doesn't exist"""
    sample_data = [
        {
            "camera_name": "Entrance Camera",
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": (datetime.now() - timedelta(days=1, hours=2)).strftime("%H:%M:%S"),
            "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
            "month": (datetime.now() - timedelta(days=1)).strftime("%Y-%m"),
            "people_count": 2
        },
        {
            "camera_name": "Backdoor Camera",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": (datetime.now() - timedelta(hours=1)).strftime("%H:%M:%S"),
            "timestamp": datetime.now().isoformat(),
            "month": datetime.now().strftime("%Y-%m"),
            "people_count": 1
        }
    ]
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump(sample_data, f, indent=4)
        logger.info("Created new data file with sample records")

def load_all_events() -> List[dict]:
    """Load all events from the JSON file"""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_data_file()
        return []

def save_event(event: dict):
    """Save a new event to the JSON file"""
    try:
        events = load_all_events()
        events.append(event)
        with open(DATA_FILE, 'w') as f:
            json.dump(events, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save event: {e}")
        return False

def get_filtered_events(date_filter: str = None, month_filter: str = None) -> List[dict]:
    """Get events filtered by date or month"""
    events = load_all_events()
    if date_filter:
        return [e for e in events if e['date'] == date_filter]
    elif month_filter:
        return [e for e in events if e['month'] == month_filter]
    return events

def get_unique_dates() -> List[str]:
    """Get all unique dates from the events"""
    events = load_all_events()
    return sorted(list(set(e['date'] for e in events)), reverse=True)

def get_unique_months() -> List[str]:
    """Get all unique months from the events"""
    events = load_all_events()
    return sorted(list(set(e['month'] for e in events)), reverse=True)

@st.cache_resource
def load_yolo_model():
    """Load the YOLO model"""
    try:
        model = YOLO('yolov8n.onnx')
        logger.info("YOLO model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None

# Initialize components
model = load_yolo_model()
initialize_data_file()

async def detection_loop(video_placeholder, table_placeholder, selected_cameras):
    """Main detection loop"""
    confidence_threshold = 0.5
    human_class_id = 0
    cooldown_duration = 30  # Reduced for testing
    last_detection_time = 0
    detections_df = pd.DataFrame(columns=["Camera", "Date", "Time", "People Count"])

    # Initialize camera captures
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
        while getattr(st.session_state, 'detection_active', False) and caps:
            current_time = time.time()
            
            # Cooldown handling
            if current_time - last_detection_time < cooldown_duration:
                remaining = int(cooldown_duration - (current_time - last_detection_time))
                table_placeholder.warning(f"Cooldown active - {remaining}s remaining")
                await asyncio.sleep(1)
                continue

            # Process each camera feed
            for cam_name, cap in caps.items():
                ret, frame = cap.read()
                if not ret:
                    continue

                try:
                    # Detect humans
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = model(frame_rgb, conf=confidence_threshold)
                    human_detections = [
                        box for result in results 
                        for box in result.boxes 
                        if int(box.cls) == human_class_id and float(box.conf) >= confidence_threshold
                    ]

                    # Annotate frame
                    annotated_frame = frame_rgb.copy()
                    for box in human_detections:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f"Person {float(box.conf):.2f}", 
                                   (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # Display info
                    cv2.putText(annotated_frame, f"Count: {len(human_detections)}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(annotated_frame, f"Camera: {cam_name}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    video_placeholder.image(annotated_frame, channels="RGB", caption=cam_name)

                    # Save detection if humans found
                    if human_detections:
                        timestamp = datetime.now()
                        event = {
                            'camera_name': cam_name,
                            'date': timestamp.strftime("%Y-%m-%d"),
                            'time': timestamp.strftime("%H:%M:%S"),
                            'timestamp': timestamp.isoformat(),
                            'month': timestamp.strftime("%Y-%m"),
                            'people_count': len(human_detections)
                        }
                        save_event(event)
                        
                        # Update live table
                        new_entry = pd.DataFrame([[
                            cam_name,
                            event['date'],
                            event['time'],
                            event['people_count']
                        ]], columns=["Camera", "Date", "Time", "People Count"])
                        
                        detections_df = pd.concat([detections_df, new_entry], ignore_index=True)
                        last_detection_time = current_time
                        table_placeholder.warning(f"Human detected! Cooldown for {cooldown_duration}s")

                    # Display live detections
                    if not detections_df.empty:
                        table_placeholder.dataframe(detections_df)

                except Exception as e:
                    logger.error(f"Processing error: {e}")

            await asyncio.sleep(0.1)

    finally:
        for cap in caps.values():
            cap.release()
        cv2.destroyAllWindows()

def display_historical_data():
    """Display historical detection data"""
    st.sidebar.header("Historical Data")
    view_option = st.sidebar.radio("View by", ["All", "Date", "Month"])
    
    if view_option == "Date":
        dates = get_unique_dates()
        selected_date = st.sidebar.selectbox("Select Date", dates)
        events = get_filtered_events(date_filter=selected_date)
    elif view_option == "Month":
        months = get_unique_months()
        selected_month = st.sidebar.selectbox("Select Month", months)
        events = get_filtered_events(month_filter=selected_month)
    else:
        events = get_filtered_events()
    
    if events:
        st.subheader("Detection History")
        # Group by date for better organization
        events_by_date = {}
        for event in sorted(events, key=lambda x: x['timestamp'], reverse=True):
            date = event['date']
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        for date, date_events in events_by_date.items():
            st.markdown(f"**{date}**")
            df = pd.DataFrame(date_events)[['time', 'camera_name', 'people_count']]
            st.dataframe(df, hide_index=True)
    else:
        st.info("No detection events found")

def main():
    st.title("Restricted Area Monitoring System")
    
    # Initialize session state
    if 'detection_active' not in st.session_state:
        st.session_state.detection_active = False
    
    # Historical data view
    display_historical_data()
    
    # Live monitoring section
    st.sidebar.header("Live Monitoring")
    cameras = [
        {"name": "Webcam", "address": 0},
        {"name": "IP Camera", "address": "rtsp://example.com/stream"}
    ]
    
    selected_cameras = st.sidebar.multiselect(
        "Select Cameras",
        [cam["name"] for cam in cameras],
        default=[cameras[0]["name"]]
    )
    
    selected_cameras = [cam for cam in cameras if cam["name"] in selected_cameras]
    
    # Start/stop buttons
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Start Monitoring") and selected_cameras:
        st.session_state.detection_active = True
        video_placeholder = st.empty()
        table_placeholder = st.empty()
        asyncio.run(detection_loop(video_placeholder, table_placeholder, selected_cameras))
    
    if col2.button("Stop Monitoring"):
        st.session_state.detection_active = False
        st.rerun()

if __name__ == "__main__":
    main()
