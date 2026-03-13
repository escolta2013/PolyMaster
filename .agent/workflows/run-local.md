---
description: How to run PolyMaster locally (Backend & Frontend)
---

# Running PolyMaster Locally

Follow these steps to launch the PolyMaster ecosystem on your machine.

## 1. Start the Backend (FastAPI)
The backend handles the tracker engine and data indexing.

```bash
cd backend
# Activate virtual environment
.\venv\Scripts\activate
# Start server
uvicorn main:app --reload --port 8000
```
The backend will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 2. Start the Frontend (Next.js)
The frontend provides the professional dashboard.

```bash
cd frontend
# Install dependencies (only first time)
npm install
# Start development server
npm run dev
```
The dashboard will be available at [http://localhost:3000](http://localhost:3000).

## 3. Verify
- Open the dashboard at [http://localhost:3000](http://localhost:3000).
- Check the "Quantum-Node" status in the header; it should indicate "Active" if the backend is running.
