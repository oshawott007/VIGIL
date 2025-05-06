
# import streamlit as st
# import cv2
# from ultralytics import YOLO
# from datetime import datetime
# import numpy as np
# import asyncio
# import logging
# from pymongo import MongoClient
# from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure
# from matplotlib import pyplot as plt
# import uuid

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # MongoDB Atlas connection
# @st.cache_resource
# def init_mongo():
#     MONGO_URI = "mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
#     try:
#         client = MongoClient(
#             MONGO_URI,
#             serverSelectionTimeoutMS=5000,
#             connectTimeoutMS=30000,
#             socketTimeoutMS=30000
#         )
#         # Test connection
#         client.admin.command('ping')
#         db = client['vigil']
#         occupancy_collection = db['occupancy_data']
#         # Verify collection accessibility
#         occupancy_collection.find_one()
#         logger.info("Connected to MongoDB Atlas successfully!")
#         st.success("Connected to MongoDB Atlas successfully!")
#         return occupancy_collection
#     except (ServerSelectionTimeoutError, ConnectionFailure) as e:
#         logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
#         st.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
#         st.write("**Troubleshooting Steps**:")
#         st.write("1. Verify MongoDB Atlas credentials")
#         st.write("2. Set Network Access to allow connections from your IP in MongoDB Atlas")
#         st.write("3. Ensure pymongo>=4.8.0 is in requirements.txt")
#         st.write("4. Check cluster status (not paused) in MongoDB Atlas")
#         return None
#     except Exception as e:
#         logger.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
#         st.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
#         return None

# occupancy_collection = init_mongo()
# if occupancy_collection is None:
#     st.error("MongoDB connection failed. Cannot proceed with occupancy dashboard.")
#     st.stop()

# # Load occupancy detection model
# @st.cache_resource
# def load_model():
#     try:
#         model = YOLO('yolov8n.onnx')
#         logger.info("Occupancy detection model loaded successfully")
#         return model
#     except Exception as e:
#         logger.error(f"Model loading failed: {str(e)}")
#         st.error(f"Model loading failed: {str(e)}")
#         st.stop()

# occ_model = load_model()
# if occ_model is None:
#     st.stop()

# # Function to load historical occupancy data
# def load_occupancy_data():
#     """Load historical occupancy data from MongoDB Atlas"""
#     if occupancy_collection is None:
#         logger.warning("No MongoDB collection available for loading occupancy data")
#         return {}
    
#     try:
#         data = {}
#         cursor = occupancy_collection.find()
#         for doc in cursor:
#             date = doc.get('date')
#             if date:
#                 data[date] = {
#                     'max_count': doc.get('max_count', 0),
#                     'hourly_counts': doc.get('hourly_counts', [0] * 24),
#                     'minute_counts': doc.get('minute_counts', [0] * 1440)
#                 }
#         logger.info("Successfully loaded historical occupancy data")
#         return data
#     except Exception as e:
#         logger.error(f"Failed to load occupancy data: {str(e)}")
#         st.warning(f"Failed to load historical occupancy data: {str(e)}")
#         return {}

# # Function to get or create today's document
# def get_today_document():
#     """Get or create today's occupancy document in MongoDB Atlas"""
#     if occupancy_collection is None:
#         logger.error("No MongoDB collection available for today's document")
#         return None
    
#     today = datetime.now().date()
#     try:
#         # Attempt to find today's document
#         document = occupancy_collection.find_one({"date": str(today)})
#         if not document:
#             # Create new document with default values
#             document = {
#                 "date": str(today),
#                 "max_count": 0,
#                 "hourly_counts": [0] * 24,
#                 "minute_counts": [0] * 1440,
#                 "last_updated": datetime.now(),
#                 "document_id": str(uuid.uuid4())  # Unique identifier for traceability
#             }
#             occupancy_collection.insert_one(document)
#             logger.info(f"Created new occupancy document for {today}")
#         else:
#             logger.info(f"Retrieved existing occupancy document for {today}")
#         return document
#     except OperationFailure as e:
#         logger.error(f"Database operation failed for today's document: {str(e)}")
#         st.error(f"Database operation failed: {str(e)}")
#         return None
#     except Exception as e:
#         logger.error(f"Failed to get or create today's document: {str(e)}")
#         st.error(f"Failed to initialize occupancy data: {str(e)}")
#         return None

# # Function to update the database
# def update_database(current_count, hourly_counts, minute_counts, max_count):
#     """Update the occupancy database with current count"""
#     if occupancy_collection is None:
#         logger.warning("No MongoDB collection available for database update")
#         return max_count, hourly_counts, minute_counts
    
#     today = datetime.now().date()
#     current_hour = datetime.now().hour
#     current_minute = datetime.now().hour * 60 + datetime.now().minute
    
#     try:
#         hourly_counts[current_hour] = max(hourly_counts[current_hour], current_count)
#         minute_counts[current_minute] = current_count
#         new_max = max(max_count, current_count)
        
#         occupancy_collection.update_one(
#             {"date": str(today)},
#             {"$set": {
#                 "max_count": new_max,
#                 "hourly_counts": hourly_counts,
#                 "minute_counts": minute_counts,
#                 "last_updated": datetime.now()
#             }},
#             upsert=True
#         )
#         logger.info(f"Updated occupancy data for {today}")
#         return new_max, hourly_counts, minute_counts
#     except Exception as e:
#         logger.error(f"Failed to update database: {str(e)}")
#         st.warning(f"Failed to update database: {str(e)}")
#         return max_count, hourly_counts, minute_counts

# # Function to detect people in a frame
# def detect_people(frame):
#     """Detect people in a frame using YOLO"""
#     if occ_model is None:
#         logger.error("No model available for person detection")
#         return frame, 0
    
#     try:
#         results = occ_model(frame, conf=0.5)
#         people_count = 0
#         for result in results:
#             for box in result.boxes:
#                 if int(box.cls) == 0:  # class 0 is person
#                     people_count += 1
#                     x1, y1, x2, y2 = map(int, box.xyxy[0])
#                     cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#                     cv2.putText(frame, f'Person: {float(box.conf):.2f}', 
#                                (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
#                                0.5, (0, 255, 0), 2)
#         return frame, people_count
#     except Exception as e:
#         logger.error(f"Failed to detect people: {str(e)}")
#         return frame, 0

# # Async function for occupancy detection loop
# async def occupancy_detection_loop(video_placeholder, stats_placeholder, 
#                                  hourly_chart_placeholder, minute_chart_placeholder):
#     """Main occupancy detection loop"""
#     caps = {}
#     frame_counter = 0
#     frame_skip = 5  # Run inference every 5th frame
#     ui_update_counter = 0
#     ui_update_skip = 3  # Update UI every 3rd frame
    
#     # Initialize video captures
#     for cam_name in st.session_state.occ_selected_cameras:
#         cam_address = next((cam['address'] for cam in st.session_state.cameras 
#                           if cam['name'] == cam_name), None)
#         if cam_address:
#             try:
#                 cap = cv2.VideoCapture(cam_address)
#                 if cap.isOpened():
#                     caps[cam_name] = cap
#                 else:
#                     logger.error(f"Failed to open camera: {cam_name}")
#                     video_placeholder.error(f"Failed to open camera: {cam_name}")
#             except Exception as e:
#                 logger.error(f"Failed to initialize camera {cam_name}: {e}")
    
#     if not caps:
#         video_placeholder.error("No valid cameras available")
#         st.stop()
#         return
    
#     # Initialize today's data
#     today_doc = get_today_document()
#     if today_doc is None:
#         video_placeholder.error("Failed to initialize occupancy data. Check MongoDB connection and permissions.")
#         st.stop()
#         return
    
#     max_count = today_doc["max_count"]
#     hourly_counts = today_doc["hourly_counts"]
#     minute_counts = today_doc.get("minute_counts", [0] * 1440)
#     last_update_minute = -1
    
#     try:
#         while st.session_state.occ_detection_active:
#             total_count = 0
#             frames = {}
            
#             current_hour = datetime.now().hour
#             current_minute = datetime.now().hour * 60 + datetime.now().minute
            
#             for cam_name, cap in caps.items():
#                 ret, frame = cap.read()
#                 if not ret:
#                     logger.error(f"Failed to capture frame from {cam_name}")
#                     continue
                
#                 # Resize frame to reduce CPU load
#                 frame = cv2.resize(frame, (640, 480))
                
#                 # Convert to RGB for inference and display
#                 frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                 annotated_frame = frame_rgb.copy()
                
#                 # Run inference every frame_skip frames
#                 count = 0
#                 if frame_counter % frame_skip == 0:
#                     annotated_frame, count = detect_people(frame_rgb)
#                     total_count += count
                
#                 cv2.putText(annotated_frame, f"Count: {count}", (10, 30),
#                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
#                 frames[cam_name] = annotated_frame
            
#             # Update counts
#             if frame_counter % frame_skip == 0:
#                 st.session_state.occ_current_count = total_count
                
#                 if current_minute != last_update_minute:
#                     max_count, hourly_counts, minute_counts = update_database(
#                         total_count, hourly_counts, minute_counts, max_count)
#                     st.session_state.occ_max_count = max_count
#                     st.session_state.occ_hourly_counts = hourly_counts
#                     st.session_state.occ_minute_counts = minute_counts
#                     last_update_minute = current_minute
            
#             # Display frames
#             if frames and ui_update_counter % ui_update_skip == 0:
#                 cols = video_placeholder.columns(min(len(frames), 2))
#                 for i, (cam_name, frame) in enumerate(frames.items()):
#                     if i < 2:  # Limit to 2 columns
#                         with cols[i]:
#                             st.image(frame, channels="RGB",
#                                     caption=f"{cam_name} - Count: {total_count}",
#                                     use_column_width=True)
            
#             # Update statistics and charts
#             with stats_placeholder.container():
#                 col1, col2 = st.columns(2)
#                 col1.metric("Current Occupancy", st.session_state.occ_current_count)
#                 col2.metric("Today's Maximum", st.session_state.occ_max_count)
                
#                 fig, ax = plt.subplots()
#                 hours = [f"{h}:00" for h in range(24)]
#                 ax.plot(hours, hourly_counts, marker='o', color='orange')
#                 ax.set_title("Hourly Maximum Occupancy")
#                 ax.set_xlabel("Hour of Day")
#                 ax.set_ylabel("Maximum People Count")
#                 plt.xticks(rotation=45)
#                 hourly_chart_placeholder.pyplot(fig)
#                 plt.close(fig)
                
#                 fig, ax = plt.subplots(figsize=(10, 4))
#                 minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
#                 ax.plot(range(1440), minute_counts, linewidth=1, color='orange')
#                 ax.set_title("Minute-by-Minute Presence")
#                 ax.set_xlabel("Time (24h)")
#                 ax.set_ylabel("People Count")
#                 ax.set_xticks(range(0, 1440, 15*4))
#                 ax.set_xticklabels(minutes[::4], rotation=45)
#                 minute_chart_placeholder.pyplot(fig)
#                 plt.close(fig)
            
#             frame_counter += 1
#             ui_update_counter += 1
#             await asyncio.sleep(0.1)  # ~10 FPS
            
#     finally:
#         for cap in caps.values():
#             try:
#                 cap.release()
#             except Exception as e:
#                 logger.error(f"Failed to release camera: {e}")
#         cv2.destroyAllWindows()
#         logger.info("Camera resources released")



import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime
import numpy as np
import asyncio
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure
from matplotlib import pyplot as plt
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Atlas connection
@st.cache_resource
def init_mongo():
    MONGO_URI = "mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000
        )
        # Test connection
        client.admin.command('ping')
        db = client['vigil']
        occupancy_collection = db['occupancy_data']
        # Verify collection accessibility
        occupancy_collection.find_one()
        logger.info("Connected to MongoDB Atlas successfully!")
        st.success("Connected to MongoDB Atlas successfully!")
        return occupancy_collection
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
        st.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
        st.write("**Troubleshooting Steps**:")
        st.write("1. Verify MongoDB Atlas credentials")
        st.write("2. Set Network Access to allow connections from your IP in MongoDB Atlas")
        st.write("3. Ensure pymongo>=4.8.0 is in requirements.txt")
        st.write("4. Check cluster status (not paused) in MongoDB Atlas")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
        st.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
        return None

occupancy_collection = init_mongo()
if occupancy_collection is None:
    st.error("MongoDB connection failed. Cannot proceed with occupancy dashboard.")
    st.stop()

# Load occupancy detection model
@st.cache_resource
def load_model():
    try:
        model = YOLO('yolov8n.onnx')
        logger.info("Occupancy detection model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Model loading failed: {str(e)}")
        st.error(f"Model loading failed: {str(e)}")
        st.stop()

occ_model = load_model()
if occ_model is None:
    st.stop()

# Function to load historical occupancy data
def load_occupancy_data(date=None, camera_name=None):
    """Load historical occupancy data from MongoDB Atlas by date and camera name"""
    if occupancy_collection is None:
        logger.warning("No MongoDB collection available for loading occupancy data")
        return {}
    
    try:
        query = {}
        if date:
            query["date"] = str(date)
        if camera_name:
            query["camera_name"] = camera_name
        
        data = {}
        cursor = occupancy_collection.find(query)
        for doc in cursor:
            date = doc.get('date')
            cam = doc.get('camera_name')
            if date and cam:
                if date not in data:
                    data[date] = {}
                data[date][cam] = {
                    'max_count': doc.get('max_count', 0),
                    'hourly_counts': doc.get('hourly_counts', [0] * 24),
                    'minute_counts': doc.get('minute_counts', [0] * 1440)
                }
        logger.info(f"Successfully loaded historical occupancy data for query: {query}")
        return data
    except Exception as e:
        logger.error(f"Failed to load occupancy data: {str(e)}")
        st.warning(f"Failed to load historical occupancy data: {str(e)}")
        return {}

# Function to get or create today's document for a specific camera
def get_today_document(camera_name):
    """Get or create today's occupancy document for a specific camera in MongoDB Atlas"""
    if occupancy_collection is None:
        logger.error("No MongoDB collection available for today's document")
        return None
    
    today = datetime.now().date()
    try:
        # Attempt to find today's document for the camera
        document = occupancy_collection.find_one({"date": str(today), "camera_name": camera_name})
        if not document:
            # Create new document with default values
            document = {
                "date": str(today),
                "camera_name": camera_name,
                "max_count": 0,
                "hourly_counts": [0] * 24,
                "minute_counts": [0] * 1440,
                "last_updated": datetime.now(),
                "document_id": str(uuid.uuid4())  # Unique identifier for traceability
            }
            occupancy_collection.insert_one(document)
            logger.info(f"Created new occupancy document for {today}, camera: {camera_name}")
        else:
            logger.info(f"Retrieved existing occupancy document for {today}, camera: {camera_name}")
        return document
    except OperationFailure as e:
        logger.error(f"Database operation failed for today's document: {str(e)}")
        st.error(f"Database operation failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to get or create today's document for camera {camera_name}: {str(e)}")
        st.error(f"Failed to initialize occupancy data for camera {camera_name}: {str(e)}")
        return None

# Function to update the database for a specific camera
def update_database(camera_name, current_count, hourly_counts, minute_counts, max_count):
    """Update the occupancy database with current count for a specific camera"""
    if occupancy_collection is None:
        logger.warning("No MongoDB collection available for database update")
        return max_count, hourly_counts, minute_counts
    
    today = datetime.now().date()
    current_hour = datetime.now().hour
    current_minute = datetime.now().hour * 60 + datetime.now().minute
    
    try:
        hourly_counts[current_hour] = max(hourly_counts[current_hour], current_count)
        minute_counts[current_minute] = current_count
        new_max = max(max_count, current_count)
        
        occupancy_collection.update_one(
            {"date": str(today), "camera_name": camera_name},
            {"$set": {
                "max_count": new_max,
                "hourly_counts": hourly_counts,
                "minute_counts": minute_counts,
                "last_updated": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Updated occupancy data for {today}, camera: {camera_name}")
        return new_max, hourly_counts, minute_counts
    except Exception as e:
        logger.error(f"Failed to update database for camera {camera_name}: {str(e)}")
        st.warning(f"Failed to update database for camera {camera_name}: {str(e)}")
        return max_count, hourly_counts, minute_counts

# Function to detect people in a frame
def detect_people(frame):
    """Detect people in a frame using YOLO"""
    if occ_model is None:
        logger.error("No model available for person detection")
        return frame, 0
    
    try:
        results = occ_model(frame, conf=0.5)
        people_count = 0
        for result in results:
            for box in result.boxes:
                if int(box.cls) == 0:  # class 0 is person
                    people_count += 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f'Person: {float(box.conf):.2f}', 
                               (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.5, (0, 255, 0), 2)
        return frame, people_count
    except Exception as e:
        logger.error(f"Failed to detect people: {str(e)}")
        return frame, 0

# Async function for occupancy detection loop
async def occupancy_detection_loop(video_placeholder, stats_placeholder, 
                                 hourly_chart_placeholder, minute_chart_placeholder):
    """Main occupancy detection loop"""
    caps = {}
    frame_counter = 0
    frame_skip = 5  # Run inference every 5th frame
    ui_update_counter = 0
    ui_update_skip = 3  # Update UI every 3rd frame
    
    # Initialize video captures
    for cam_name in st.session_state.occ_selected_cameras:
        cam_address = next((cam['address'] for cam in st.session_state.cameras 
                          if cam['name'] == cam_name), None)
        if cam_address:
            try:
                cap = cv2.VideoCapture(cam_address)
                if cap.isOpened():
                    caps[cam_name] = cap
                else:
                    logger.error(f"Failed to open camera: {cam_name}")
                    video_placeholder.error(f"Failed to open camera: {cam_name}")
            except Exception as e:
                logger.error(f"Failed to initialize camera {cam_name}: {e}")
    
    if not caps:
        video_placeholder.error("No valid cameras available")
        st.stop()
        return
    
    # Initialize today's data for each camera
    camera_data = {}
    for cam_name in caps.keys():
        today_doc = get_today_document(cam_name)
        if today_doc is None:
            video_placeholder.error(f"Failed to initialize occupancy data for camera {cam_name}")
            st.stop()
            return
        camera_data[cam_name] = {
            'max_count': today_doc["max_count"],
            'hourly_counts': today_doc["hourly_counts"],
            'minute_counts': today_doc.get("minute_counts", [0] * 1440),
            'last_update_minute': -1
        }
    
    try:
        while st.session_state.occ_detection_active:
            total_count = 0
            frames = {}
            
            current_hour = datetime.now().hour
            current_minute = datetime.now().hour * 60 + datetime.now().minute
            
            for cam_name, cap in caps.items():
                ret, frame = cap.read()
                if not ret:
                    logger.error(f"Failed to capture frame from {cam_name}")
                    continue
                
                # Resize frame to reduce CPU load
                frame = cv2.resize(frame, (640, 480))
                
                # Convert to RGB for inference and display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                annotated_frame = frame_rgb.copy()
                
                # Run inference every frame_skip frames
                count = 0
                if frame_counter % frame_skip == 0:
                    annotated_frame, count = detect_people(frame_rgb)
                    total_count += count
                
                cv2.putText(annotated_frame, f"Count: {count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                frames[cam_name] = annotated_frame
                
                # Update counts for this camera
                if frame_counter % frame_skip == 0:
                    cam_data = camera_data[cam_name]
                    if current_minute != cam_data['last_update_minute']:
                        cam_data['max_count'], cam_data['hourly_counts'], cam_data['minute_counts'] = update_database(
                            cam_name, count, cam_data['hourly_counts'], cam_data['minute_counts'], cam_data['max_count']
                        )
                        cam_data['last_update_minute'] = current_minute
                        camera_data[cam_name] = cam_data
            
            # Update total count for display
            if frame_counter % frame_skip == 0:
                st.session_state.occ_current_count = total_count
                st.session_state.occ_max_count = max([cam_data['max_count'] for cam_data in camera_data.values()])
                st.session_state.occ_hourly_counts = [sum(counts) for counts in zip(*[cam_data['hourly_counts'] for cam_data in camera_data.values()])]
                st.session_state.occ_minute_counts = [sum(counts) for counts in zip(*[cam_data['minute_counts'] for cam_data in camera_data.values()])]
            
            # Display frames
            if frames and ui_update_counter % ui_update_skip == 0:
                cols = video_placeholder.columns(min(len(frames), 2))
                for i, (cam_name, frame) in enumerate(frames.items()):
                    if i < 2:  # Limit to 2 columns
                        with cols[i]:
                            st.image(frame, channels="RGB",
                                    caption=f"{cam_name} - Count: {camera_data[cam_name]['max_count']}",
                                    use_column_width=True)
            
            # Update statistics and charts
            with stats_placeholder.container():
                col1, col2 = st.columns(2)
                col1.metric("Current Occupancy", st.session_state.occ_current_count)
                col2.metric("Today's Maximum", st.session_state.occ_max_count)
                
                fig, ax = plt.subplots()
                hours = [f"{h}:00" for h in range(24)]
                ax.plot(hours, st.session_state.occ_hourly_counts, marker='o', color='orange')
                ax.set_title("Hourly Maximum Occupancy (All Cameras)")
                ax.set_xlabel("Hour of Day")
                ax.set_ylabel("Maximum People Count")
                plt.xticks(rotation=45)
                hourly_chart_placeholder.pyplot(fig)
                plt.close(fig)
                
                fig, ax = plt.subplots(figsize=(10, 4))
                minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
                ax.plot(range(1440), st.session_state.occ_minute_counts, linewidth=1, color='orange')
                ax.set_title("Minute-by-Minute Presence (All Cameras)")
                ax.set_xlabel("Time (24h)")
                ax.set_ylabel("People Count")
                ax.set_xticks(range(0, 1440, 15*4))
                ax.set_xticklabels(minutes[::4], rotation=45)
                minute_chart_placeholder.pyplot(fig)
                plt.close(fig)
            
            frame_counter += 1
            ui_update_counter += 1
            await asyncio.sleep(0.1)  # ~10 FPS
            
    finally:
        for cap in caps.values():
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Failed to release camera: {e}")
        cv2.destroyAllWindows()
        logger.info("Camera resources released")

