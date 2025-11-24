# Use Python 3.11 slim image (more stable for Google ADK)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip show google-adk

# Create a non-root user for security
RUN useradd -m -u 1000 adkuser && chown -R adkuser:adkuser /app

# Copy application code
COPY --chown=adkuser:adkuser . .

# Switch to non-root user
USER adkuser

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8080

# Run the ADK Web UI - serves the frontend interface
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080", "."]
