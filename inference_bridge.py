import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import joblib
import pandas as pd
import time
import numpy as np
import threading

# Load the models
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
stage1_path = os.path.join(base_dir, "ml", "hydracure_virtual_ph.pkl")
stage2_path = os.path.join(base_dir, "ml", "hydracure_toxicity_classifier.pkl")

print("Loading ML models...")
try:
    regressor = joblib.load(stage1_path)
    classifier = joblib.load(stage2_path)
    print("Models loaded successfully.")
except Exception as e:
    print(f"Error loading models: {e}")
    exit(1)

# Initialize Firebase Admin
print("Initializing Firebase...")
try:
    # Attempt to initialize with default credentials
    # Ensure you have set the GOOGLE_APPLICATION_CREDENTIALS environment variable
    # OR replace with credentials.Certificate('path/to/serviceAccountKey.json')
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://iot-basics-5ba4b-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
except Exception as e:
    # If serviceAccountKey.json is not found, fallback to default or prompt user
    print(f"Failed to load serviceAccountKey.json: {e}")
    print("Please ensure serviceAccountKey.json is present in the directory.")
    exit(1)

print("Firebase initialized.")

def listener_callback(event):
    if event.data is None:
        return
        
    try:
        # Fetch latest state from database root or nodes
        root_data = db.reference('/').get()
        if not isinstance(root_data, dict):
            return

        tds_node = root_data.get('tds', {})
        turb_node = root_data.get('turbidity', {})
        temp_node = root_data.get('temperature', {}) or root_data.get('temp', {})
        ph_node = root_data.get('ph', {})

        tds = float(tds_node.get('tds', 0) if isinstance(tds_node, dict) else (tds_node or 0))
        turbidity = float(turb_node.get('ntu', turb_node.get('turbidity', 0)) if isinstance(turb_node, dict) else (turb_node or 0))
        temp = float(temp_node.get('celsius', temp_node.get('temp', 25)) if isinstance(temp_node, dict) else (temp_node or 25))
        ph = float(ph_node.get('ph', 7.0) if isinstance(ph_node, dict) else (ph_node or 7.0))

        process_data(tds, turbidity, temp, ph)
    except Exception as e:
        print(f"Listener error: {e}")

def process_data(tds, turbidity, temp, ph=7.0):
    try:
        # Stage 1: Predict Virtual/Inferred pH baseline
        input_stage1 = np.array([[tds, turbidity, temp]])
        virtual_ph = float(regressor.predict(input_stage1)[0]) if regressor else ph
        
        # Stage 2: Predict Toxicity Risk Level using actual or inferred pH
        input_stage2 = np.array([[tds, turbidity, ph]])
        risk_level = classifier.predict(input_stage2)[0] if classifier else "SAFE"
        
        if isinstance(risk_level, np.generic):
            risk_level = risk_level.item()
            
        ref = db.reference('live_monitoring/inference_results')
        result_payload = {
            'virtual_ph': ph,
            'risk_level': risk_level,
            'timestamp': int(time.time() * 1000)
        }
        ref.push(result_payload)
        print(f"Inference complete. pH: {ph:.2f}, Risk Level: {risk_level}")
        
    except Exception as e:
        print(f"Error during inference: {e}")

# Start listening to root database for any sensor update
listener_ref = db.reference('/')
listener = listener_ref.listen(listener_callback)

print("Listening for sensor updates on root database...")

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down listener...")
    listener.close()
