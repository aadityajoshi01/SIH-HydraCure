import joblib
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import warnings
import time

# 1. Suppress those Version Warnings for the Presentation
warnings.filterwarnings("ignore", category=UserWarning)

# 2. Firebase Configuration
# Replace 'service_key.json' with your actual filename if it's different
FIREBASE_URL = "https://ml-model-6951b-default-rtdb.asia-southeast1.firebasedatabase.app/"

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("service_key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_URL
        })
        print("🔗 Connected to Firebase Successfully")
    except Exception as e:
        print(f"❌ Firebase Connection Error: {e}")

# 3. Load the AI Models (Goal 2 & Goal 3)
try:
    # Goal 2: Inferred pH
    ph_model = joblib.load('ph_predictor.pkl')
    # Goal 3: Safety & Pollution Logic
    safety_model = joblib.load('goal3_safety_engine.pkl')
    pollution_model = joblib.load('goal3_pollution_model.pkl')
    print("🧠 All AI Models Loaded: Goal 2 & Goal 3 Active")
except Exception as e:
    print(f"❌ Model Loading Error: {e}")

# 4. The Integrated Inference Engine
def run_hydracure_inference(event):
    # This function triggers every time your ESP32 updates the /sensors node
    try:
        # Get live data
        data = db.reference('/sensors').get()
        
        if data and 'tds' in data and 'turbidity' in data:
            tds = data['tds']
            turbidity = data['turbidity']

            # --- STEP 1: GOAL 2 (Predict pH) ---
            # Features: ['Solids', 'Turbidity']
            ph_features = pd.DataFrame([[tds, turbidity]], columns=['Solids', 'Turbidity'])
            predicted_ph = ph_model.predict(ph_features)[0]

            # --- STEP 2: GOAL 3 (Safety & Pollution) ---
            # Features: ['pH', 'Turbidity (NTU)']
            # We use the pH we JUST predicted as an input for the metal/safety check
            goal3_features = pd.DataFrame([[predicted_ph, turbidity]], columns=['pH', 'Turbidity (NTU)'])
            
            is_unsafe = safety_model.predict(goal3_features)[0] # 0 = Safe, 1 = Unsafe
            pollution_lv = pollution_model.predict(goal3_features)[0] # Levels 1-4

            # --- STEP 3: LOGIC & ALERTS ---
            safety_status = "🚨 UNSAFE: Heavy Metal Risk" if is_unsafe == 1 else "✅ Water Status: Safe"
            
            # --- STEP 4: UPDATE DASHBOARD ---
            db.reference('/ai_analytics').update({
                'predicted_ph': round(float(predicted_ph), 2),
                'safety_status': safety_status,
                'pollution_level': int(pollution_lv),
                'last_inference': time.strftime("%H:%M:%S")
            })

            print(f"[{time.strftime('%H:%M:%S')}] pH: {predicted_ph:.2f} | Status: {safety_status} | Level: {pollution_lv}")
        else:
            print("⏳ Waiting for sensor data from ESP32...")

    except Exception as e:
        print(f"⚠️ Inference Loop Error: {e}")

# 5. Start the Real-Time Listener
print("🚀 HydraCure AI Engine: Online and Listening for Sensor Data...")
db.reference('/sensors').listen(run_hydracure_inference)