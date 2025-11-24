# ADK Playground

A simple weather and time assistant built with Google's Agent Development Kit (ADK).

## What This Agent Does

This agent can answer questions about:
- Current weather in major cities (New York, San Francisco, London)
- Current time in various cities (New York, San Francisco, London, Tokyo, Paris)

## Prerequisites

- Python 3.10+
- Google API Key (from [Google AI Studio](https://aistudio.google.com/)) OR Vertex AI access
- Docker (optional, for containerized deployment)

## Local Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up authentication:**

   Create a `.env` file with your Google API key:
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

   Or for Vertex AI:
   ```bash
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   ```

3. **Run the agent:**

   **Web UI (recommended for testing):**
   ```bash
   adk web
   ```

   **Terminal mode:**
   ```bash
   adk run adk-playground
   ```

   **API Server:**
   ```bash
   adk api_server
   ```

## Docker Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t adk-weather-agent:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8080:8080 \
     -e GOOGLE_API_KEY=your_api_key_here \
     adk-weather-agent:latest
   ```

3. **Access the API:**
   The agent will be available at `http://localhost:8080`

## Docker Compose (Optional)

Create a `docker-compose.yml` file:
```yaml
version: '3.8'
services:
  adk-agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    restart: unless-stopped
```

Run with:
```bash
docker-compose up
```

## Example Queries

- "What's the weather in New York?"
- "What time is it in Tokyo?"
- "Tell me about the weather and time in San Francisco"

## Project Structure

```
adk-playground/
├── agent.py           # Main agent definition
├── __init__.py        # Package initialization
├── requirements.txt   # Python dependencies
├── Dockerfile         # Docker configuration
├── .dockerignore      # Docker ignore file
└── README.md          # This file
```

## Extending the Agent

To add more cities or capabilities:

1. Update the `get_weather()` function with more cities
2. Add timezones to the `timezone_map` in `get_current_time()`
3. Create new tool functions and add them to the `tools` list in the Agent

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Python GitHub](https://github.com/google/adk-python)
- [ADK Samples](https://github.com/google/adk-samples)
