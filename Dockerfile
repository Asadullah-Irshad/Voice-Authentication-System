# ═══════════════════════════════════════════════════════════════════════════
#  Voice Authentication System — production image
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim

# System deps: ffmpeg for audio decoding, build-essential for wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Install Python deps first for better layer caching
COPY Backend/requirements.txt ./Backend/requirements.txt
RUN pip install --upgrade pip && pip install -r Backend/requirements.txt

# Copy the application
COPY Backend ./backend
COPY Frontend ./frontend

WORKDIR /srv/Backend

EXPOSE 8000

# A non-root user for safety
RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
