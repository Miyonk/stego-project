FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
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
COPY --chown=user data ./data
COPY --chown=user results ./results
COPY --chown=user --from=web /web/dist ./frontend/dist
EXPOSE 7860
CMD ["uvicorn", "api.app_deploy:app", "--host", "0.0.0.0", "--port", "7860"]
