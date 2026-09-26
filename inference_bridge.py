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
    # Search common locations for the service account key
    key_candidates = [
        os.environ.get('FIREBASE_SERVICE_KEY', ''),
        os.path.join(base_dir, 'serviceAccountKey.json'),
        os.path.join(base_dir, 'service_key.json'),
        os.path.join(base_dir, 'HydraCure ML', 'service_key.json'),
    ]
    key_path = next((p for p in key_candidates if p and os.path.isfile(p)), None)
    if key_path is None:
        raise FileNotFoundError('no service account key found')
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://iot-basics-5ba4b-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
    print(f"Using service key: {key_path}")
except Exception as e:
    print(f"Failed to load Firebase service account key: {e}")
    print("Please place serviceAccountKey.json (or service_key.json) in the project root.")
    exit(1)

# Warn early when the key belongs to a different Firebase project than the sensor DB
try:
    import json as _json
    with open(key_path, encoding='utf-8') as f:
        key_project = _json.load(f).get('project_id', '')
    if key_project and key_project != 'iot-basics-5ba4b':
        print(f"⚠️  WARNING: this key belongs to project '{key_project}', but the sensor database is 'iot-basics-5ba4b'.")
        print("   In the Firebase console (iot-basics-5ba4b project): Project settings → Service accounts →")
        print("   Generate new private key, and save it as serviceAccountKey.json in the project root.")
except Exception:
    pass

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
        # Model was trained with features in this exact order:
        # ['Turbidity (NTU)', 'Temperature (°C)', 'TDS (mg/L)']
        input_stage1 = np.array([[turbidity, temp, tds]])
        predicted_ph = float(regressor.predict(input_stage1)[0]) if regressor else ph

        # Stage 2: Predict Toxicity Risk Level using the inferred pH
        # Model features: ['Predicted_pH', 'Turbidity (NTU)', 'TDS (mg/L)']
        input_stage2 = np.array([[predicted_ph, turbidity, tds]])
        risk_level = classifier.predict(input_stage2)[0] if classifier else "SAFE"
        confidence = float(np.max(classifier.predict_proba(input_stage2)[0])) if classifier is not None and hasattr(classifier, 'predict_proba') else None

        if isinstance(risk_level, np.generic):
            risk_level = risk_level.item()

        # A prediction is only valid when every sensor feeding the model reports real data
        valid = tds > 0 and turbidity > 0 and 0 < temp < 100

        ref = db.reference('live_monitoring/inference_results')
        result_payload = {
            'virtual_ph': round(predicted_ph, 2),
            'measured_ph': ph,
            'risk_level': risk_level,
            'confidence': round(confidence, 3) if confidence is not None else '',
            'valid': bool(valid),
            'timestamp': int(time.time() * 1000)
        }
        ref.push(result_payload)
        conf_str = f"{confidence * 100:.0f}%" if confidence is not None else "n/a"
        print(f"Inference complete. Virtual pH: {predicted_ph:.2f}, Risk: {risk_level}, Confidence: {conf_str}, Valid: {valid}")

    except Exception as e:
        print(f"Error during inference: {e}")

# Start listening to root database for any sensor update
listener_ref = db.reference('/')
try:
    listener = listener_ref.listen(listener_callback)
except Exception as e:
    print(f"❌ Could not start Firebase listener: {e}")
    print("   The service account key was rejected. Fix it in the Firebase console:")
    print("   1. IAM & Admin → Settings → enable 'Service account authentication support' for RTDB, and/or")
    print("   2. IAM & Admin → Grant the service account the 'Firebase Realtime Database Admin' role, then rerun start.bat.")
    exit(1)

print("Listening for sensor updates on root database...")

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down listener...")
    listener.close()
