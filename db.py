# db.py
from pymongo import MongoClient

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://infernapeamber:g9kASflhhSQ26GMF@cluster0.mjoloub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
 # Replace with your MongoDB Atlas URI
client = MongoClient(MONGO_URI)
db = client['vigil_db']  # Database name
cameras_collection = db['cameras']  # Collection for cameras
fire_settings_collection = db['fire_settings']  # Collection for fire detection settings
occupancy_settings_collection = db['occupancy_settings']  # Collection for occupancy settings
tailgating_settings_collection = db['tailgating_settings']  # Collection for tailgating settings
no_access_settings_collection = db['no_access_settings']  # Collection for no-access settings

def add_camera_to_db(name, address):
    """Add a camera to MongoDB."""
    camera = {"name": name, "address": address}
    cameras_collection.insert_one(camera)
    return camera

def get_cameras_from_db():
    """Retrieve all cameras from MongoDB."""
    return list(cameras_collection.find())

def remove_camera_from_db(camera_id):
    """Remove a camera from MongoDB by its ID."""
    cameras_collection.delete_one({"_id": camera_id})

def save_selected_cameras(collection, selected_cameras):
    """Save selected cameras for a specific module."""
    collection.replace_one({}, {"selected_cameras": selected_cameras}, upsert=True)

def get_selected_cameras(collection):
    """Retrieve selected cameras for a specific module."""
    doc = collection.find_one()
    return doc.get("selected_cameras", []) if doc else []
