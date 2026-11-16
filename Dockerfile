# ── Stage 1: Build Frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Build Python Backend Dependencies ───────────────────────
FROM python:3.11-slim AS backend-builder
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Unified Production Container ────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Nginx, curl, and gettext-base (for envsubst)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

# Copy Python virtual environment
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Backend Application
COPY backend/ /app/backend/

# Copy Frontend Build into Nginx web root
COPY --from=frontend-builder /app/frontend/dist /var/www/frontend

# Copy Nginx template and startup script
COPY deployment/nginx.unified.conf.template /etc/nginx/templates/default.conf.template
COPY deployment/start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["/app/start.sh"]

