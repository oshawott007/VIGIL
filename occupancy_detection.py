# import streamlit as st
# import cv2
# from ultralytics import YOLO
# from datetime import datetime, date, timedelta
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

# # Function to clean up invalid documents
# def clean_invalid_documents():
#     """Detect and optionally delete invalid documents from the occupancy_data collection"""
#     if occupancy_collection is None:
#         logger.warning("No MongoDB collection available for cleaning documents")
#         return 0
    
#     invalid_docs = []
#     try:
#         cursor = occupancy_collection.find()
#         for doc in cursor:
#             if not all(key in doc for key in ['date', 'camera_name', 'max_count', 'hourly_counts', 'minute_counts']):
#                 invalid_docs.append({
#                     'document_id': doc.get('document_id', 'unknown'),
#                     'missing_fields': [key for key in ['date', 'camera_name', 'max_count', 'hourly_counts', 'minute_counts'] if key not in doc]
#                 })
#             elif not isinstance(doc['max_count'], (int, float)) or \
#                  not isinstance(doc['hourly_counts'], list) or len(doc['hourly_counts']) != 24 or \
#                  not isinstance(doc['minute_counts'], list) or len(doc['minute_counts']) != 1440:
#                 invalid_docs.append({
#                     'document_id': doc.get('document_id', 'unknown'),
#                     'error': "Incorrect field types or lengths"
#                 })
        
#         if invalid_docs:
#             st.warning(f"Found {len(invalid_docs)} invalid documents:")
#             for doc in invalid_docs:
#                 st.write(f"- Document ID: {doc['document_id']}, Issue: {doc.get('missing_fields', doc.get('error'))}")
            
#             if st.button("Delete Invalid Documents"):
#                 for doc in invalid_docs:
#                     occupancy_collection.delete_one({"document_id": doc['document_id']})
#                 logger.info(f"Deleted {len(invalid_docs)} invalid documents")
#                 st.success(f"Deleted {len(invalid_docs)} invalid documents")
#                 return len(invalid_docs)
#         return 0
#     except Exception as e:
#         logger.error(f"Failed to clean invalid documents: {str(e)}")
#         st.error(f"Failed to clean invalid documents: {str(e)}")
#         return 0

# # Function to insert default data for May 5, 2025, Cam Road
# def insert_default_data():
#     """Insert default occupancy data for May 5, 2025, for Cam Road"""
#     if occupancy_collection is None:
#         logger.warning("No MongoDB collection available for inserting default data")
#         return
    
#     default_date = "2025-05-05"
#     camera_name = "Cam Road"
    
#     # Check if data already exists
#     existing_doc = occupancy_collection.find_one({"date": default_date, "camera_name": camera_name})
#     if existing_doc:
#         logger.info(f"Default data for {default_date}, {camera_name} already exists")
#         return
    
#     # Create sample data
#     hourly_counts = [0, 0, 0, 0, 2, 5, 8, 10, 12, 15, 10, 8, 6, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0]
#     minute_counts = [0] * 1440
#     # Simulate activity from 8:00 to 12:00
#     for minute in range(480, 720):  # 8:00 to 12:00
#         minute_counts[minute] = np.random.randint(0, 15)
#     max_count = max(minute_counts) if minute_counts else 0
    
#     default_doc = {
#         "date": default_date,
#         "camera_name": camera_name,
#         "max_count": max_count,
#         "hourly_counts": hourly_counts,
#         "minute_counts": minute_counts,
#         "last_updated": datetime(2025, 5, 5, 23, 59, 59),
#         "document_id": str(uuid.uuid4())
#     }
    
#     try:
#         occupancy_collection.insert_one(default_doc)
#         logger.info(f"Inserted default data for {default_date}, {camera_name}")
#     except Exception as e:
#         logger.error(f"Failed to insert default data: {str(e)}")
#         st.warning(f"Failed to insert default data: {str(e)}")

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
# def load_occupancy_data(date=None, camera_name=None):
#     """Load historical occupancy data from MongoDB Atlas by date and camera name"""
#     if occupancy_collection is None:
#         logger.warning("No MongoDB collection available for loading occupancy data")
#         return {}
    
#     try:
#         query = {}
#         if date:
#             query["date"] = str(date)
#         if camera_name:
#             query["camera_name"] = camera_name
        
#         data = {}
#         cursor = occupancy_collection.find(query)
#         for doc in cursor:
#             date = doc.get('date')
#             cam = doc.get('camera_name')
#             # Validate required fields
#             missing_fields = [key for key in ['date', 'camera_name', 'max_count', 'hourly_counts', 'minute_counts'] if key not in doc]
#             if missing_fields:
#                 logger.warning(f"Skipping invalid document: missing fields {missing_fields} in {doc.get('document_id', 'unknown')}")
#                 continue
#             if not isinstance(doc['max_count'], (int, float)) or \
#                not isinstance(doc['hourly_counts'], list) or len(doc['hourly_counts']) != 24 or \
#                not isinstance(doc['minute_counts'], list) or len(doc['minute_counts']) != 1440:
#                 logger.warning(f"Skipping invalid document: incorrect field types or lengths in {doc.get('document_id', 'unknown')}")
#                 continue
            
#             if date and cam:
#                 if date not in data:
#                     data[date] = {}
#                 data[date][cam] = {
#                     'max_count': doc['max_count'],
#                     'hourly_counts': doc['hourly_counts'],
#                     'minute_counts': doc['minute_counts']
#                 }
#         logger.info(f"Successfully loaded historical occupancy data for query: {query}")
#         return data
#     except Exception as e:
#         logger.error(f"Failed to load occupancy data: {str(e)}")
#         st.warning(f"Failed to load historical occupancy data: {str(e)}")
#         return {}

# # Function to get or create today's document for a specific camera
# def get_today_document(camera_name):
#     """Get or create today's occupancy document for a specific camera in MongoDB Atlas"""
#     if occupancy_collection is None:
#         logger.error("No MongoDB collection available for today's document")
#         return None
    
#     today = datetime.now().date()
#     try:
#         document = occupancy_collection.find_one({"date": str(today), "camera_name": camera_name})
#         if not document:
#             document = {
#                 "date": str(today),
#                 "camera_name": camera_name,
#                 "max_count": 0,
#                 "hourly_counts": [0] * 24,
#                 "minute_counts": [0] * 1440,
#                 "last_updated": datetime.now(),
#                 "document_id": str(uuid.uuid4())
#             }
#             occupancy_collection.insert_one(document)
#             logger.info(f"Created new occupancy document for {today}, camera: {camera_name}")
#         else:
#             logger.info(f"Retrieved existing occupancy document for {today}, camera: {camera_name}")
#         return document
#     except OperationFailure as e:
#         logger.error(f"Database operation failed for today's document: {str(e)}")
#         st.error(f"Database operation failed: {str(e)}")
#         return None
#     except Exception as e:
#         logger.error(f"Failed to get or create today's document for camera {camera_name}: {str(e)}")
#         st.error(f"Failed to initialize occupancy data for camera {camera_name}: {str(e)}")
#         return None

# # Function to update the database for a specific camera
# def update_database(camera_name, current_count, hourly_counts, minute_counts, max_count):
#     """Update the occupancy database with current count for a specific camera"""
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
#             {"date": str(today), "camera_name": camera_name},
#             {"$set": {
#                 "max_count": new_max,
#                 "hourly_counts": hourly_counts,
#                 "minute_counts": minute_counts,
#                 "last_updated": datetime.now()
#             }},
#             upsert=True
#         )
#         logger.info(f"Updated occupancy data for {today}, camera: {camera_name}")
#         return new_max, hourly_counts, minute_counts
#     except Exception as e:
#         logger.error(f"Failed to update database for camera {camera_name}: {str(e)}")
#         st.warning(f"Failed to update database for camera {camera_name}: {str(e)}")
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

# # Function to display historical data
# def display_historical_data():
#     """Display historical occupancy data for a selected date and camera"""
#     st.sidebar.header("View Historical Data")
#     selected_date = st.sidebar.date_input("Select Date", value=date(2025, 5, 5))
#     camera_options = st.session_state.get('occ_selected_cameras', ["Cam Road"])
#     selected_camera = st.sidebar.selectbox("Select Camera", camera_options, index=0)
    
#     if st.sidebar.button("Load Historical Data"):
#         historical_data = load_occupancy_data(date=selected_date, camera_name=selected_camera)
#         date_str = str(selected_date)
        
#         if date_str in historical_data and selected_camera in historical_data[date_str]:
#             data = historical_data[date_str][selected_camera]
#             st.subheader(f"Occupancy Data for {selected_camera} on {selected_date}")
            
#             # Display max count
#             st.metric("Maximum Occupancy", data['max_count'])
            
#             # Plot hourly counts
#             fig, ax = plt.subplots()
#             hours = [f"{h}:00" for h in range(24)]
#             ax.plot(hours, data['hourly_counts'], marker='o', color='orange')
#             ax.set_title(f"Hourly Maximum Occupancy - {selected_camera}")
#             ax.set_xlabel("Hour of Day")
#             ax.set_ylabel("Maximum People Count")
#             plt.xticks(rotation=45)
#             st.pyplot(fig)
#             plt.close(fig)
            
#             # Plot minute counts
#             fig, ax = plt.subplots(figsize=(10, 4))
#             minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
#             ax.plot(range(1440), data['minute_counts'], linewidth=1, color='orange')
#             ax.set_title(f"Minute-by-Minute Presence - {selected_camera}")
#             ax.set_xlabel("Time (24h)")
#             ax.set_ylabel("People Count")
#             ax.set_xticks(range(0, 1440, 15*4))
#             ax.set_xticklabels(minutes[::4], rotation=45)
#             st.pyplot(fig)
#             plt.close(fig)
#         else:
#             st.error(f"No data found for {selected_camera} on {selected_date}.")

# # Async function for occupancy detection loop
# async def occupancy_detection_loop(video_placeholder, stats_placeholder, 
#                                  hourly_chart_placeholder, minute_chart_placeholder):
#     """Main occupancy detection loop"""
#     # Insert default data for May 5, 2025, Cam Road
#     insert_default_data()
    
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
    
#     # Initialize today's data for each camera
#     camera_data = {}
#     for cam_name in caps.keys():
#         today_doc = get_today_document(cam_name)
#         if today_doc is None:
#             video_placeholder.error(f"Failed to initialize occupancy data for camera {cam_name}")
#             st.stop()
#             return
#         camera_data[cam_name] = {
#             'max_count': today_doc["max_count"],
#             'hourly_counts': today_doc["hourly_counts"],
#             'minute_counts': today_doc.get("minute_counts", [0] * 1440),
#             'last_update_minute': -1
#         }
    
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
                
#                 # Update counts for this camera
#                 if frame_counter % frame_skip == 0:
#                     cam_data = camera_data[cam_name]
#                     if current_minute != cam_data['last_update_minute']:
#                         cam_data['max_count'], cam_data['hourly_counts'], cam_data['minute_counts'] = update_database(
#                             cam_name, count, cam_data['hourly_counts'], cam_data['minute_counts'], cam_data['max_count']
#                         )
#                         cam_data['last_update_minute'] = current_minute
#                         camera_data[cam_name] = cam_data
            
#             # Update total count for display
#             if frame_counter % frame_skip == 0:
#                 st.session_state.occ_current_count = total_count
#                 st.session_state.occ_max_count = max([cam_data['max_count'] for cam_data in camera_data.values()])
#                 st.session_state.occ_hourly_counts = [sum(counts) for counts in zip(*[cam_data['hourly_counts'] for cam_data in camera_data.values()])]
#                 st.session_state.occ_minute_counts = [sum(counts) for counts in zip(*[cam_data['minute_counts'] for cam_data in camera_data.values()])]
            
#             # Display frames
#             if frames and ui_update_counter % ui_update_skip == 0:
#                 cols = video_placeholder.columns(min(len(frames), 2))
#                 for i, (cam_name, frame) in enumerate(frames.items()):
#                     if i < 2:  # Limit to 2 columns
#                         with cols[i]:
#                             st.image(frame, channels="RGB",
#                                     caption=f"{cam_name} - Count: {camera_data[cam_name]['max_count']}",
#                                     use_column_width=True)
            
#             # Update statistics and charts
#             with stats_placeholder.container():
#                 col1, col2 = st.columns(2)
#                 col1.metric("Current Occupancy", st.session_state.occ_current_count)
#                 col2.metric("Today's Maximum", st.session_state.occ_max_count)
                
#                 fig, ax = plt.subplots()
#                 hours = [f"{h}:00" for h in range(24)]
#                 ax.plot(hours, st.session_state.occ_hourly_counts, marker='o', color='orange')
#                 ax.set_title("Hourly Maximum Occupancy (All Cameras)")
#                 ax.set_xlabel("Hour of Day")
#                 ax.set_ylabel("Maximum People Count")
#                 plt.xticks(rotation=45)
#                 hourly_chart_placeholder.pyplot(fig)
#                 plt.close(fig)
                
#                 fig, ax = plt.subplots(figsize=(10, 4))
#                 minutes = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
#                 ax.plot(range(1440), st.session_state.occ_minute_counts, linewidth=1, color='orange')
#                 ax.set_title("Minute-by-Minute Presence (All Cameras)")
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

# # Main application
# def main():
#     # Ensure Cam Road is in the list of cameras
#     if 'occ_selected_cameras' not in st.session_state:
#         st.session_state.occ_selected_cameras = ["Cam Road"]
#     if 'cameras' not in st.session_state:
#         st.session_state.cameras = [{"name": "Cam Road", "address": "0"}]  # Dummy address for testing
    
#     # Initialize session state variables
#     if 'occ_detection_active' not in st.session_state:
#         st.session_state.occ_detection_active = False
#     if 'occ_current_count' not in st.session_state:
#         st.session_state.occ_current_count = 0
#     if 'occ_max_count' not in st.session_state:
#         st.session_state.occ_max_count = 0
#     if 'occ_hourly_counts' not in st.session_state:
#         st.session_state.occ_hourly_counts = [0] * 24
#     if 'occ_minute_counts' not in st.session_state:
#         st.session_state.occ_minute_counts = [0] * 1440
    
#     st.title("Occupancy Dashboard")
    
#     # Placeholders for video and stats
#     video_placeholder = st.empty()
#     stats_placeholder = st.empty()
#     hourly_chart_placeholder = st.empty()
#     minute_chart_placeholder = st.empty()
    
#     # Clean invalid documents interface
#     st.sidebar.header("Database Maintenance")
#     if st.sidebar.button("Check for Invalid Documents"):
#         clean_invalid_documents()
    
#     # Display historical data interface
#     display_historical_data()
    
#     # Start/stop detection button
#     if st.button("Start/Stop Detection"):
#         st.session_state.occ_detection_active = not st.session_state.occ_detection_active
    
#     # Run detection loop if active
#     if st.session_state.occ_detection_active:
#         asyncio.run(occupancy_detection_loop(
#             video_placeholder, stats_placeholder,
#             hourly_chart_placeholder, minute_chart_placeholder
#         ))

# if __name__ == "__main__":
#     main()





import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime, date
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
        client.admin.command('ping')
        db = client['vigil']
        occupancy_collection = db['occupancy_data']
        occupancy_collection.find_one()
        logger.info("Connected to MongoDB Atlas successfully!")
        st.success("Connected to MongoDB Atlas successfully!")
        return occupancy_collection
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
        st.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
        st.write("**Troubleshooting Steps**:")
        st.write("1. Verify MongoDB Atlas credentials")
        st.write("2. Set Network Access to allow connections from your IP")
        st.write("3. Ensure pymongo>=4.8.0 is installed")
        st.write("4. Check cluster status in MongoDB Atlas")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
        st.error(f"Unexpected error connecting to MongoDB Atlas: {str(e)}")
        return None

occupancy_collection = init_mongo()
if occupancy_collection is None:
    st.error("MongoDB connection failed. Cannot proceed with occupancy dashboard.")
    st.stop()

# Load YOLO model
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

# Function to check MongoDB collection status
def check_collection_status():
    """Check the status of the MongoDB collection and list all documents"""
    if occupancy_collection is None:
        st.error("No MongoDB collection available")
        return
    
    try:
        count = occupancy_collection.count_documents({})
        st.write(f"Total documents in collection: {count}")
        if count == 0:
            st.warning("No documents found. Inserting default data...")
            insert_default_data()
            count = occupancy_collection.count_documents({})
            st.write(f"After inserting default data, total documents: {count}")
        
        st.write("### Documents in Collection")
        cursor = occupancy_collection.find()
        for doc in cursor:
            st.write(f"- Date: {doc.get('date', 'N/A')}, Camera: {doc.get('camera_name', 'N/A')}, "
                     f"Document ID: {doc.get('document_id', 'N/A')}, "
                     f"Presence Length: {len(doc.get('presence', []))}, "
                     f"Hourly Max Counts Length: {len(doc.get('hourly_max_counts', []))}")
    except Exception as e:
        logger.error(f"Failed to check collection status: {str(e)}")
        st.error(f"Failed to check collection status: {str(e)}")

# Function to insert default data for May 4 and May 5, 2025
def insert_default_data():
    """Insert default occupancy data for May 4 and May 5, 2025, for Cam Road and Cam Hall"""
    if occupancy_collection is None:
        logger.warning("No MongoDB collection available for inserting default data")
        return
    
    default_dates = ["2025-05-04", "2025-05-05"]
    cameras = ["Cam Road", "Cam Hall"]
    
    for default_date in default_dates:
        for camera_name in cameras:
            # Delete existing documents to ensure fresh data
            occupancy_collection.delete_many({"date": default_date, "camera_name": camera_name})
            logger.info(f"Deleted existing documents for {default_date}, {camera_name}")
            
            # Create sample data
            presence = [0] * 1440  # Minute-by-minute presence (1 or 0)
            hourly_max_counts = [0] * 24  # Max people per hour
            
            # Simulate different patterns for each date
            if default_date == "2025-05-04":
                # Activity from 7:00 to 11:00 and 15:00 to 18:00
                for minute in range(420, 660):  # 7:00 to 11:00
                    presence[minute] = np.random.choice([0, 1], p=[0.4, 0.6])  # 60% chance of presence
                for minute in range(900, 1080):  # 15:00 to 18:00
                    presence[minute] = np.random.choice([0, 1], p=[0.5, 0.5])  # 50% chance of presence
                for hour in range(24):
                    max_count = max(np.random.randint(0, 8, size=10)) if hour in range(7, 11) or hour in range(15, 18) else 0
                    hourly_max_counts[hour] = max_count
            else:  # 2025-05-05
                # Activity from 8:00 to 12:00 and 14:00 to 17:00
                for minute in range(480, 720):  # 8:00 to 12:00
                    presence[minute] = np.random.choice([0, 1], p=[0.3, 0.7])  # 70% chance of presence
                for minute in range(840, 1020):  # 14:00 to 17:00
                    presence[minute] = np.random.choice([0, 1], p=[0.4, 0.6])  # 60% chance of presence
                for hour in range(24):
                    max_count = max(np.random.randint(0, 10, size=10)) if hour in range(8, 12) or hour in range(14, 17) else 0
                    hourly_max_counts[hour] = max_count
            
            default_doc = {
                "date": default_date,
                "camera_name": camera_name,
                "presence": presence,
                "hourly_max_counts": hourly_max_counts,
                "last_updated": datetime(2025, 5, 4 if default_date == "2025-05-04" else 5, 23, 59, 59),
                "document_id": str(uuid.uuid4())
            }
            
            try:
                occupancy_collection.insert_one(default_doc)
                logger.info(f"Inserted default data for {default_date}, {camera_name}")
            except Exception as e:
                logger.error(f"Failed to insert default data for {camera_name}: {str(e)}")
                st.warning(f"Failed to insert default data for {camera_name}: {str(e)}")

# Function to get or create today's document for a specific camera
def get_today_document(camera_name):
    """Get or create today's occupancy document for a specific camera"""
    if occupancy_collection is None:
        logger.error("No MongoDB collection available for today's document")
        return None
    
    today = datetime.now().date()
    try:
        document = occupancy_collection.find_one({"date": str(today), "camera_name": camera_name})
        if not document:
            document = {
                "date": str(today),
                "camera_name": camera_name,
                "presence": [0] * 1440,
                "hourly_max_counts": [0] * 24,
                "last_updated": datetime.now(),
                "document_id": str(uuid.uuid4())
            }
            occupancy_collection.insert_one(document)
            logger.info(f"Created new occupancy document for {today}, {camera_name}")
        return document
    except OperationFailure as e:
        logger.error(f"Database operation failed for today's document: {str(e)}")
        st.error(f"Database operation failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to get or create today's document for {camera_name}: {str(e)}")
        st.error(f"Failed to initialize occupancy data for {camera_name}: {str(e)}")
        return None

# Function to update the database for a specific camera
def update_database(camera_name, presence, hourly_max_counts, current_count, current_minute, current_hour):
    """Update the occupancy database for a specific camera"""
    if occupancy_collection is None:
        logger.warning("No MongoDB collection available for database update")
        return presence, hourly_max_counts
    
    today = datetime.now().date()
    try:
        presence[current_minute] = 1 if current_count > 0 else presence[current_minute]
        hourly_max_counts[current_hour] = max(hourly_max_counts[current_hour], current_count)
        
        occupancy_collection.update_one(
            {"date": str(today), "camera_name": camera_name},
            {"$set": {
                "presence": presence,
                "hourly_max_counts": hourly_max_counts,
                "last_updated": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Updated occupancy data for {today}, {camera_name}")
        return presence, hourly_max_counts
    except Exception as e:
        logger.error(f"Failed to update database for {camera_name}: {str(e)}")
        st.warning(f"Failed to update database for {camera_name}: {str(e)}")
        return presence, hourly_max_counts

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
                if int(box.cls) == 0:  # Class 0 is person
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

# Function to plot minute-by-minute presence as a circular clock
def plot_presence_clock(presence, camera_name, date_str):
    """Plot minute-by-minute presence as a circular clock"""
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    theta = np.linspace(0, 2 * np.pi, 1440, endpoint=False)  # Angles for 1440 minutes
    radius = np.array(presence)  # 1 or 0 for presence
    
    # Plot bars for presence
    bars = ax.bar(theta[radius == 1], radius[radius == 1], width=2*np.pi/1440, color='orange', alpha=0.7)
    ax.set_yticks([])  # Hide radial ticks
    ax.set_xticks(np.linspace(0, 2*np.pi, 24, endpoint=False))
    ax.set_xticklabels([f"{h}:00" for h in range(24)], fontsize=10)
    ax.set_title(f"Minute-by-Minute Presence - {camera_name} on {date_str}", pad=20)
    
    # Ensure clock starts at 12:00 and goes clockwise
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    
    return fig

# Function to plot hourly maximum occupancy
def plot_hourly_occupancy(hourly_max_counts, camera_name, date_str):
    """Plot hourly maximum occupancy as a line graph"""
    fig, ax = plt.subplots(figsize=(10, 4))
    hours = [f"{h}:00" for h in range(24)]
    ax.plot(hours, hourly_max_counts, marker='o', color='blue')
    ax.set_title(f"Hourly Maximum Occupancy - {camera_name} on {date_str}")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Maximum People Count")
    plt.xticks(rotation=45)
    ax.grid(True)
    return fig

# Function to load historical or today's data
def load_occupancy_data(date=None):
    """Load occupancy data from MongoDB Atlas for a specific date"""
    if occupancy_collection is None:
        logger.warning("No MongoDB collection available for loading occupancy data")
        return {}
    
    try:
        query = {"date": str(date)} if date else {}
        logger.info(f"Executing query: {query}")
        data = {}
        cursor = occupancy_collection.find(query)
        doc_count = 0
        valid_doc_count = 0
        
        for doc in cursor:
            doc_count += 1
            missing_fields = [key for key in ['date', 'camera_name', 'presence', 'hourly_max_counts'] if key not in doc]
            if missing_fields:
                logger.warning(f"Skipping invalid document: missing fields {missing_fields} in {doc.get('document_id', 'unknown')}")
                continue
            if not isinstance(doc['presence'], list) or len(doc['presence']) != 1440 or \
               not isinstance(doc['hourly_max_counts'], list) or len(doc['hourly_max_counts']) != 24:
                logger.warning(f"Skipping invalid document: incorrect field lengths in {doc.get('document_id', 'unknown')}")
                continue
            
            date_str = doc['date']
            cam = doc['camera_name']
            if date_str not in data:
                data[date_str] = {}
            data[date_str][cam] = {
                'presence': doc['presence'],
                'hourly_max_counts': doc['hourly_max_counts']
            }
            valid_doc_count += 1
        
        logger.info(f"Processed {doc_count} documents, {valid_doc_count} valid for query: {query}")
        return data
    except Exception as e:
        logger.error(f"Failed to load occupancy data: {str(e)}")
        st.warning(f"Failed to load occupancy data: {str(e)}")
        return {}

# Async function for occupancy detection loop
async def occupancy_detection_loop(video_placeholder, stats_placeholder):
    """Main occupancy detection loop for multiple cameras"""
    # Insert default data for testing
    insert_default_data()
    
    caps = {}
    frame_counter = 0
    frame_skip = 5  # Run inference every 5th frame
    
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
            video_placeholder.error(f"Failed to initialize occupancy data for {cam_name}")
            st.stop()
            return
        camera_data[cam_name] = {
            'presence': today_doc['presence'],
            'hourly_max_counts': today_doc['hourly_max_counts'],
            'last_update_minute': -1
        }
    
    try:
        while st.session_state.occ_detection_active:
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
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                annotated_frame = frame_rgb.copy()
                
                # Run inference every frame_skip frames
                count = 0
                if frame_counter % frame_skip == 0:
                    annotated_frame, count = detect_people(frame_rgb)
                
                cv2.putText(annotated_frame, f"Count: {count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                frames[cam_name] = annotated_frame
                
                # Update data for this camera
                if frame_counter % frame_skip == 0:
                    cam_data = camera_data[cam_name]
                    if current_minute != cam_data['last_update_minute']:
                        cam_data['presence'], cam_data['hourly_max_counts'] = update_database(
                            cam_name, cam_data['presence'], cam_data['hourly_max_counts'],
                            count, current_minute, current_hour
                        )
                        cam_data['last_update_minute'] = current_minute
                        camera_data[cam_name] = cam_data
            
            # Display frames
            if frames:
                cols = video_placeholder.columns(min(len(frames), 2))
                for i, (cam_name, frame) in enumerate(frames.items()):
                    if i < 2:
                        with cols[i]:
                            st.image(frame, channels="RGB",
                                    caption=f"{cam_name} - Count: {camera_data[cam_name]['hourly_max_counts'][datetime.now().hour]}",
                                    use_column_width=True)
            
            # Update stats
            with stats_placeholder.container():
                for cam_name in camera_data:
                    st.metric(f"Current Max ({cam_name})", 
                             camera_data[cam_name]['hourly_max_counts'][current_hour])
            
            frame_counter += 1
            await asyncio.sleep(0.1)  # ~10 FPS
            
    finally:
        for cap in caps.values():
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Failed to release camera: {e}")
        cv2.destroyAllWindows()
        logger.info("Camera resources released")

# Function to display historical data
def display_historical_data():
    """Display historical or today's data for selected date"""
    st.sidebar.header("View Historical Data")
    selected_date = st.sidebar.date_input("Select Date", value=date(2025, 5, 5))
    
    if st.sidebar.button("Load Data"):
        historical_data = load_occupancy_data(selected_date)
        date_str = str(selected_date)
        
        if date_str in historical_data and historical_data[date_str]:
            st.subheader(f"Data for {selected_date}")
            for camera_name in historical_data[date_str]:
                st.write(f"### {camera_name}")
                col1, col2 = st.columns(2)
                
                # Minute-by-minute presence (circular clock)
                with col1:
                    fig = plot_presence_clock(historical_data[date_str][camera_name]['presence'],
                                           camera_name, selected_date)
                    st.pyplot(fig)
                    plt.close(fig)
                
                # Hourly maximum occupancy
                with col2:
                    fig = plot_hourly_occupancy(historical_data[date_str][camera_name]['hourly_max_counts'],
                                              camera_name, selected_date)
                    st.pyplot(fig)
                    plt.close(fig)
        else:
            st.error(f"No historical occupancy data available for {selected_date}. "
                     f"Please check if data exists in MongoDB or try inserting default data.")
            st.write("**Troubleshooting Steps**:")
            st.write("1. Use 'Check MongoDB Status' to verify documents.")
            st.write("2. Ensure default data for 2025-05-04 and 2025-05-05 is inserted.")
            st.write("3. Check MongoDB logs for insertion errors.")

# Main application
def main():
    # Initialize session state
    if 'occ_selected_cameras' not in st.session_state:
        st.session_state.occ_selected_cameras = ["Cam Road", "Cam Hall"]
    if 'cameras' not in st.session_state:
        st.session_state.cameras = [
            {"name": "Cam Road", "address": "0"},
            {"name": "Cam Hall", "address": "0"}
        ]
    if 'occ_detection_active' not in st.session_state:
        st.session_state.occ_detection_active = False
    
    st.title("Occupancy Dashboard")
    
    # Placeholders
    video_placeholder = st.empty()
    stats_placeholder = st.empty()
    
    # MongoDB status check interface
    st.sidebar.header("MongoDB Status")
    if st.sidebar.button("Check MongoDB Status"):
        check_collection_status()
    
    # Display historical data interface
    display_historical_data()
    
    # Start/stop detection button
    if st.button("Start/Stop Detection"):
        st.session_state.occ_detection_active = not st.session_state.occ_detection_active
    
    # Run detection loop if active
    if st.session_state.occ_detection_active:
        asyncio.run(occupancy_detection_loop(video_placeholder, stats_placeholder))

if __name__ == "__main__":
    main()
