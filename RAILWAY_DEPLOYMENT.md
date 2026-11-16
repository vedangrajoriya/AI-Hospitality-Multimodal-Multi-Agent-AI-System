# 🚂 Railway Deployment Guide: Celestial Concierge

This guide walks you through deploying **Celestial Concierge** (FastAPI backend + React frontend) to [Railway](https://railway.com) in production.

---

## 🏗️ Architecture on Railway

The repository is configured as a monorepo containing two separate Railway services:

```
                      ┌───────────────────────────────────────────────┐
                      │             Railway Project                   │
                      │                                               │
                      │  ┌─────────────────┐     ┌─────────────────┐  │
                      │  │ Frontend Service│     │ Backend Service │  │
                      │  │  (React/Nginx)  │────▶│ (FastAPI/CrewAI)│  │
                      │  │  Root: frontend │     │  Root: backend  │  │
                      │  └─────────────────┘     └─────────────────┘  │
                      └───────────────────────────────────────────────┘
```

Both services include their own optimized **`Dockerfile`**, **`railway.json`**, and support Railway's dynamic **`$PORT`** injection.

---

## 📋 Prerequisites

1. A [Railway Account](https://railway.com).
2. Your project pushed to a GitHub repository.
3. API Keys:
   - **`GROQ_API_KEY`**: For CrewAI agents & Groq LLM narratives.
   - **`DEAPI_API_KEY`**: For Flux image generation.

---

## 🚀 Step 1: Deploy the Backend Service

1. Go to your [Railway Dashboard](https://railway.com/dashboard) and click **"New Project"**.
2. Select **"Deploy from GitHub repo"** and choose your repository.
3. Once created, click on the newly created service and go to **Settings**:
   - **Service Name**: Rename it to `backend` (e.g., `celestial-backend`).
   - **Root Directory**: Set to `backend`.
4. Railway will automatically detect `backend/Dockerfile` and `backend/railway.json`.
5. Go to the **Variables** tab and add the following environment variables:

| Variable | Value / Description | Required? |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Your Groq API key (`gsk_...`) | **Yes** |
| `DEAPI_API_KEY` | Your deAPI API key | **Yes** |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Optional (default) |
| `DEAPI_IMAGE_MODEL` | `flux-1.1-schnell` | Optional (default) |
| `DEAPI_BASE_URL` | `https://api.deapi.ai` | Optional (default) |
| `LOG_LEVEL` | `INFO` | Optional |

6. Go to **Settings** > **Networking**:
   - Click **"Generate Domain"** to get a public URL (e.g., `https://celestial-backend-production.up.railway.app`).
7. **Verify Backend Health**:
   - Open your browser or curl:
     ```bash
     curl https://<your-backend-domain>.up.railway.app/health
     ```
   - Expected response: `{"status":"healthy","service":"ai-hospitality-platform"}`.

---

## 🎨 Step 2: Deploy the Frontend Service

1. In the **same Railway project**, click **"+ New"** > **"GitHub Repo"** and select the same repository again.
2. Click on this second service and go to **Settings**:
   - **Service Name**: Rename it to `frontend` (e.g., `celestial-frontend`).
   - **Root Directory**: Set to `frontend`.
3. Railway will automatically detect `frontend/Dockerfile` and `frontend/railway.json`.
4. Go to the **Variables** tab and configure:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://<your-backend-domain>.up.railway.app` | **Your public backend Railway URL from Step 1** |

> [!IMPORTANT]
> Ensure `VITE_API_URL` has **no trailing slash** (e.g., `https://celestial-backend-production.up.railway.app`). Vite embeds this at build time so the browser communicates with your Railway backend.

5. Go to **Settings** > **Networking**:
   - Click **"Generate Domain"** to get your public frontend domain (e.g., `https://celestial-frontend-production.up.railway.app`).

---

## 🔍 Step 3: Verification & Live Test

1. Visit your public frontend domain in your web browser.
2. Enter a destination (e.g., `Kyoto, Japan`), duration (e.g., `5`), budget (e.g., `$3,500`), and select interests.
3. Click **"Synthesize Experience"**.
4. Observe the interactive loading sequence as the CrewAI agents and GenAI pipelines run:
   - **Researcher & Writer**: Curates attractions and builds the day-by-day itinerary.
   - **Budget Analyst**: Formulates expense breakdown.
   - **Hotel Advisor**: Selects boutique & luxury accommodations.
   - **Groq & Flux**: Produces the narrative description and generates destination images.
5. Review the resulting glassmorphic travel dashboard.

---

## 🛠️ Features Included for Railway

- **Dynamic `$PORT` Support**: Both backend (FastAPI/Uvicorn) and frontend (Nginx template) adapt to Railway's assigned port dynamically.
- **Production Multi-Stage Dockerfiles**:
  - `backend/Dockerfile`: Minimal Debian-slim image with compiled dependencies in a virtual environment running as a non-root user.
  - `frontend/Dockerfile`: Multi-stage build producing static assets served by high-performance Nginx with Gzip compression and SPA routing.
- **Self-Healing Health Checks**: Pre-configured `/health` route and `railway.json` descriptors for automated zero-downtime deploys.
- **CORS Configured**: FastAPI is configured to allow requests from any frontend domain.

