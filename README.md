# SafeRoute AI

Safety-aware navigation: detects road hazards from imagery, scores routes by safety,
interprets plain-language preferences, and explains the recommendation.

See `PRD.md` and `TRD.md` for product/technical design, and
`specs/001-safe-route-navigation/` for the full specification.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
# For real hazard detection (optional, heavy):
pip install opencv-python ultralytics
# Build the React frontend:
cd frontend
npm install
npm run build
cd ..
```

## Configuration

Copy the variables below into your environment (see `backend/config.py`):

```text
GOOGLE_MAPS_API_KEY=...
LLM_API_KEY=...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
SAFETY_DECAY_LAMBDA=0.15
DETECTION_CONFIDENCE_THRESHOLD=0.4
SEGMENT_LENGTH_M=300
IMAGERY_STALENESS_DAYS=180
LOG_RETENTION_DAYS=30
SQLITE_PATH=backend/saferoute.db
```

## Run

```powershell
python backend/app.py
```

API + the built React frontend are served at http://localhost:5000
(Flask serves `frontend/dist` with an SPA fallback).

For frontend development with hot reload, run `npm run dev` in `frontend/`
(Vite dev server on http://localhost:5173, proxying `/api` to the Flask backend).

## Tests

```powershell
python -m pytest backend/tests/unit backend/tests/contract backend/tests/integration
```

## Model training

Fine-tune YOLOv8 on RDD2020 + extra hazard classes:

```powershell
python ml/training/train.py
```

Weights are written to `ml/weights/best.pt` (git-ignored).
