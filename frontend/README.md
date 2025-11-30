# Multi-Agent RL Frontend

Simple React frontend consuming FastAPI backend.

## Setup

```cmd
cd frontend
npm create vite@latest . -- --template react
npm install axios recharts
```

## Dev server

```cmd
npm run dev
```

Ensure backend is running:

```cmd
uvicorn src.api.main:app --reload --port 8000
```
