# Stage 1: Build the React frontend
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with system dependencies (ffmpeg, libsndfile)
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user src ./src
COPY --chown=user api ./api
COPY --chown=user configs ./configs
COPY --chown=user deploy_space/data ./data
COPY --chown=user deploy_space/results ./results
COPY --chown=user --from=web /web/dist ./frontend/dist

EXPOSE 8000 10000 7860
CMD ["sh", "-c", "uvicorn api.app_deploy:app --host 0.0.0.0 --port ${PORT:-8000}"]
