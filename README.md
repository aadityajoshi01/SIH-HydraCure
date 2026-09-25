# HydraCure – Smart Water Quality Monitoring System

HydraCure is a practical water-quality monitoring system built to track critical parameters such as pH, temperature, turbidity, and TDS, then present the readings through a web dashboard and a Python-based ML inference layer.

## Architecture

```text
Frontend (Netlify)  --->  Backend (Node.js/Express)  --->  Python ML service
      |                              |                           |
      |-- static dashboard           |-- REST API                 |-- joblib models
      |                              |-- CSV data store          |-- Firebase listener
      |                              |-- analysis logic
```

## Components

### Frontend
- Static HTML/CSS/JS site deployed on Netlify
- Base directory: `frontend`
- Publish directory: `.`
- Communicates with the backend via `API_BASE_URL`

### Backend
- Node.js + Express API service
- Exposes REST endpoints for health checks, data ingestion, analysis, and CSV export
- Reads and writes backend data files from `backend/data/`

### ML
- Python inference service running independently from Node
- Loads machine learning models from `backend/HydraCure ML/`
- Can run via `python inference_bridge.py` from the backend directory

## Communication flow

- The frontend reads `API_BASE_URL` from `frontend/js/config.js`
- Frontend requests data from the deployed backend URL
- Backend validates input and responds with JSON
- Python inference can run separately and communicate with Firebase or local APIs as configured

## Frontend deployment (Netlify)

1. Connect the GitHub repository to Netlify.
2. Set Base directory to `frontend`.
3. Leave the build command empty.
4. Set Publish directory to `.`.
5. Update `frontend/js/config.js` to point at the deployed backend domain.

## Backend deployment

Deploy the backend separately on a Node.js-capable host (Render, Railway, Heroku, Azure App Service, etc.).

Set the environment variable:

- `FRONTEND_URL=https://your-netlify-site.netlify.app`
- `PORT=8000`

Then point `API_BASE_URL` in the frontend to the backend domain.

## Local development

### Frontend
Open `frontend/index.html` directly in a browser, or serve the folder with a static file server.

### Node backend
```bash
cd backend
npm install
npm start
```

### Python ML service
```bash
cd backend
pip install -r requirements.txt
python inference_bridge.py
```

## Existing API endpoints

- `GET /api/health`
- `POST /api/sensor-data`
- `POST /api/analyze`
- `GET /api/data`
- `GET /api/export`

## Notes

- Keep all backend files and private model/data assets inside `backend/`.
- Do not expose secrets or credentials in the frontend.
- Use `backend/.env.example` as the template for production values.
