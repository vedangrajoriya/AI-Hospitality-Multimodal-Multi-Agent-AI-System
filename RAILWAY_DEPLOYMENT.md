# 🚂 Railway Single-Service Deployment: Celestial Concierge

Deploy **both frontend and backend together** under a **single service** on [Railway](https://railway.com).

---

## 🏗️ How the Single Service Architecture Works

In this unified deployment:
- **Root `Dockerfile`**: Multi-stage build that compiles the React 19 frontend into static files and builds the Python 3.11 FastAPI virtual environment.
- **Nginx Reverse Proxy**: Listens on Railway's `$PORT`.
  - Serves the frontend single-page application at `/`.
  - Reverse-proxies all backend API calls (`/generate-experience`, `/health`, `/docs`) directly to the local FastAPI server (`127.0.0.1:8000`).
- **Zero CORS Issues**: Since both frontend and backend are served from the same domain, there are no cross-origin errors or separate domains needed.
- **Single Service Cost**: You only run 1 service on Railway, saving resources and setup complexity.

```
                  ┌───────────────────────────────────────────────┐
                  │             Railway Single Service            │
                  │                                               │
                  │              Public Port ($PORT)              │
                  │                       │                       │
                  │                       ▼                       │
                  │              ┌─────────────────┐              │
                  │              │  Nginx Gateway  │              │
                  │              └────────┬────────┘              │
                  │           ┌───────────┴───────────┐           │
                  │           │                       │           │
                  │     / (Static Web)         /generate-experience│
                  │           │                /health            │
                  │           ▼                       │           │
                  │ ┌───────────────────┐             ▼           │
                  │ │   React 19 App    │    ┌──────────────────┐ │
                  │ │ (Three.js Glass)  │    │ FastAPI + CrewAI │ │
                  │ │ (/var/www/frontend│    │ (127.0.0.1:8000) │ │
                  │ └───────────────────┘    └──────────────────┘ │
                  └───────────────────────────────────────────────┘
```

---

## 🚀 Step-by-Step Deployment Instructions

### Step 1: Connect your Repository
1. In your **[Railway Dashboard](https://railway.com/dashboard)**, click **"New Project"**.
2. Select **"Deploy from GitHub repo"** and choose your repository.
3. Keep the **Root Directory** as the default: `/`.
4. Railway will automatically detect the root **`Dockerfile`** and **`railway.json`**.

---

### Step 2: Set Environment Variables
In your Railway service, navigate to the **Variables** tab, click **"RAW Editor"**, and paste:

```env
GROQ_API_KEY=your_groq_api_key_here
DEAPI_API_KEY=your_deapi_key_here
GROQ_MODEL=openai/gpt-oss-120b
DEAPI_IMAGE_MODEL=Flux1schnell
DEAPI_BASE_URL=https://api.deapi.ai
LOG_LEVEL=INFO
```

*(You do **not** need to set `VITE_API_URL` or `PORT` — Nginx and Railway handle routing and ports automatically).*

---

### Step 3: Generate Domain & Launch
1. Go to **Settings** ➔ **Networking**.
2. Click **"Generate Domain"** (e.g., `https://celestial-concierge-production.up.railway.app`).
3. Open the generated domain in your browser!
4. The React application with 3D particles will load, and clicking **"Synthesize Experience"** will seamlessly query the backend on the same domain.
