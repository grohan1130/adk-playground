# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

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

# Run the ADK API server
CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8080"]
