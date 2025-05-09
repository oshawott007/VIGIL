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
import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
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
DATA_FILE = "no_access.json"

def init_json_storage():
    try:
        # Sample data for testing historical view
        sample_data = [
            {
                'camera_name': "Entrance Camera",
                'date': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                'time': "10:15:32",
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
                'month': (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
            },
            {
                'camera_name': "Backdoor Camera",
                'date': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                'time': "14:22:45",
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
                'month': (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
            },
            {
                'camera_name': "Warehouse Camera",
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': "09:05:12",
                'timestamp': datetime.now().isoformat(),
                'month': datetime.now().strftime("%Y-%m")
            }
        ]

        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w') as f:
                json.dump(sample_data, f)
            logger.info("Created new data file with sample records")
        else:
            # If file exists but is empty, add sample data
            with open(DATA_FILE, 'r') as f:
                try:
                    existing_data = json.load(f)
                    if not existing_data:
                        with open(DATA_FILE, 'w') as f:
                            json.dump(sample_data, f)
                        logger.info("Added sample records to empty data file")
                except json.JSONDecodeError:
                    with open(DATA_FILE, 'w') as f:
                        json.dump(sample_data, f)
                    logger.info("Created new data file (invalid JSON)")
    except Exception as e:
        logger.error(f"Failed to initialize JSON storage: {e}")

def save_no_access_event(camera_name: str, human_count: int):
    try:
        timestamp = datetime.now()
        event = {
            'camera_name': camera_name,
            'date': timestamp.strftime("%Y-%m-%d"),
            'time': timestamp.strftime("%H:%M:%S"),
            'timestamp': timestamp.isoformat(),
            'month': timestamp.strftime("%Y-%m"),
            'human_count': human_count
        }
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        data.append(event)
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
            
        return True
    except Exception as e:
        logger.error(f"Failed to save event: {e}")
        return None

def load_no_access_data(date_filter: str = None, month_filter: str = None) -> Dict[str, List[dict]]:
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        filtered_data = []
        for event in data:
            if date_filter and event['date'] == date_filter:
                filtered_data.append(event)
            elif month_filter and event['month'] == month_filter:
                filtered_data.append(event)
            elif not date_filter and not month_filter:
                filtered_data.append(event)
        
        organized_data = {}
        for event in filtered_data:
            date = event['date']
            if date not in organized_data:
                organized_data[date] = []
            entry = {
                'timestamp': datetime.fromisoformat(event['timestamp']),
                'camera_name': event['camera_name'],
                'time': event['time']
            }
            organized_data[date].append(entry)
        
        for date in organized_data:
            organized_data[date].sort(key=lambda x: x['timestamp'], reverse=True)
        
        return organized_data
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {}

def get_available_dates() -> List[str]:
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        dates = list(set(event['date'] for event in data))
        return sorted(dates, reverse=True)
    except Exception as e:
        logger.error(f"Failed to get dates: {e}")
        return []

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
init_json_storage()

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
                        save_no_access_event(cam_name, len(human_detections))
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

def main():
    st.title("Restricted Area Monitoring System")
    
    # Historical Data View Section
    st.sidebar.header("Historical Data")
    view_option = st.sidebar.radio("View by", ["All Data", "Date", "Month"])
    
    if view_option == "Date":
        available_dates = get_available_dates()
        selected_date = st.sidebar.selectbox("Select Date", available_dates)
        historical_data = load_no_access_data(date_filter=selected_date)
    elif view_option == "Month":
        available_months = sorted(list(set(d[:7] for d in get_available_dates())), reverse=True)
        selected_month = st.sidebar.selectbox("Select Month", available_months)
        historical_data = load_no_access_data(month_filter=selected_month)
    else:
        historical_data = load_no_access_data()
    
    if historical_data:
        st.subheader("Detection History")
        for date, events in historical_data.items():
            st.markdown(f"**{date}**")
            df = pd.DataFrame(events)
            df = df[['time', 'camera_name']]  # Don't show timestamp column
            st.table(df)
    else:
        st.info("No historical data available")

    # Live Monitoring Section
    st.sidebar.header("Live Monitoring")
    cameras = [
        {"name": "Camera 1", "address": 0},
        {"name": "Camera 2", "address": "http://example.com/stream"}
    ]
    
    selected_camera_names = st.sidebar.multiselect(
        "Select Cameras",
        [cam["name"] for cam in cameras],
        default=[cameras[0]["name"]]
    )
    
    selected_cameras = [cam for cam in cameras if cam["name"] in selected_camera_names]
    
    if st.sidebar.button("Start Monitoring"):
        st.session_state.no_access_detection_active = True
        video_placeholder = st.empty()
        table_placeholder = st.empty()
        asyncio.run(no_access_detection_loop(video_placeholder, table_placeholder, selected_cameras))
    
    if st.sidebar.button("Stop Monitoring"):
        if 'no_access_detection_active' in st.session_state:
            st.session_state.no_access_detection_active = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()
