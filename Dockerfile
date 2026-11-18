# Production Dockerfile for GTA 6 AI Shorts Automation Agent (24/7 Cloud Daemon)
FROM python:3.12-slim

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies: FFmpeg, media libraries, fonts for subtitles
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu \
    fonts-freefont-ttf \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure essential storage directories exist
RUN mkdir -p input output/candidates output/final output/buffer database logs templates assets/bgm assets/sfx assets/fonts

# Expose web dashboard port (FastAPI / Streamlit)
EXPOSE 8000 8501

# Default command: run the 24/7 background automation daemon
CMD ["python", "daemon_service.py"]
