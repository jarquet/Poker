FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install web dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Run from src/ so imports (game, betting, etc.) work
WORKDIR /app/src

EXPOSE 3076

# Bind to 0.0.0.0 so it's reachable from the local network
CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "3076"]
