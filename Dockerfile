# ── Base image ──
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies (cached layer) ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-cache ChromaDB's ONNX embedding model ──
# Copied from local cache to avoid slow/timeout downloads at runtime
COPY onnx_models /root/.cache/chroma/onnx_models

# ── Copy application code ──
COPY . .

# ── Expose port ──
EXPOSE 8000

# ── Start the app ──
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
