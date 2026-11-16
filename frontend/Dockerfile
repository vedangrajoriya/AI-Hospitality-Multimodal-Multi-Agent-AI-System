# Stage 1: Build React/Vite Frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source code
COPY . .

# Build argument for backend API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build Vite application for production
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine

# Remove default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built frontend assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx template for dynamic $PORT injection on Railway
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Default port fallback
ENV PORT=80
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

