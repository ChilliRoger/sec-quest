# ── sec-quest Dockerfile ──────────────────────────────────────────────────
# HuggingFace Spaces: port 7860, runs as non-root user 1000
# Build: docker build -t sec-quest .
# Run:   docker run -p 7860:7860 sec-quest
# ─────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# HF Spaces expects port 7860
EXPOSE 7860

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies
COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app

# Set PYTHONPATH so imports resolve correctly
ENV PYTHONPATH=/app
ENV ENABLE_WEB_INTERFACE=true

# Switch to non-root user
USER 1000

# Start the FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]