# ====================================================================
# LOBO AI Leads — container image
# --------------------------------------------------------------------
# A small, production-ready image for Railway / Render / any Docker host.
# Credentials are NEVER baked in — provide them at runtime via env vars
# (GOOGLE_SERVICE_ACCOUNT_JSON) or a mounted secret file.
# ====================================================================

# Slim Python base keeps the image small; pin the version for repeatability.
FROM python:3.11-slim

# Don't write .pyc files; flush logs immediately (so cloud logs are live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (separate layer = better build caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app/ ./app/

# Run as a non-root user for safety.
RUN useradd --create-home appuser
USER appuser

# Start the autonomous watcher + pipeline.
CMD ["python", "-m", "app.main"]
