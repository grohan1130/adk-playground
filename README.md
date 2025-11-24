# ADK Playground

A simple weather and time assistant built with Google's Agent Development Kit (ADK).

## What This Agent Does

This agent can answer questions about:
- Current weather in major cities (New York, San Francisco, London)
- Current time in various cities (New York, San Francisco, London, Tokyo, Paris)

## Prerequisites

- Docker & Docker Compose (recommended for easiest setup)
- OR Python 3.11+ for local development
- Google API Key (from [Google AI Studio](https://aistudio.google.com/)) OR Vertex AI access

## Important: ADK Agent Directory Structure

**ADK requires each agent to be in its own subdirectory!**

The `adk web` and `adk api_server` commands scan for subdirectories containing agent files. Your project structure must be:

```
your-project/
  ├── agent_name/          ← Each agent in its own subdirectory
  │   ├── __init__.py      ← Required
  │   └── agent.py         ← Contains root_agent definition
  ├── docker-compose.yml
  └── Dockerfile
```

**This will NOT work:** Having `agent.py` directly in the project root will result in 404 errors.

## Quick Start (Docker Compose - Recommended)

1. **Create a `.env` file with your Google API key:**
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Access the ADK Web UI:**
   Open your browser to **http://localhost:8080/**

   You'll see the ADK Dev UI where you can select your agent and start chatting!

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the container:**
   ```bash
   docker-compose down
   ```

## Local Development Setup

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

   **Web UI with Frontend (Recommended):**
   ```bash
   adk web .
   ```
   This starts the ADK Dev UI at http://localhost:8000 with a browser interface.

   **API Server Only (No Frontend):**
   ```bash
   adk api_server .
   ```
   This runs just the backend API for custom frontends. Use `adk web` if you want the built-in UI!

## Alternative: Manual Docker Deployment

If you prefer to use Docker without Docker Compose:

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

3. **Access the Web UI:**
   Open your browser to `http://localhost:8080`

**Note:** Docker Compose (shown above in Quick Start) is recommended as it's easier to manage.

## Example Queries

- "What's the weather in New York?"
- "What time is it in Tokyo?"
- "Tell me about the weather and time in San Francisco"

## Project Structure

```
adk-playground/
├── weather_agent/           # Agent subdirectory (REQUIRED!)
│   ├── __init__.py         # Exports root_agent
│   └── agent.py            # Main agent definition with root_agent
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Docker ignore file
├── .env                    # Environment variables (not in git)
├── .env.example            # Example environment variables
└── README.md               # This file
```

**Key Points:**
- Each agent MUST be in its own subdirectory (e.g., `weather_agent/`)
- The subdirectory must contain `__init__.py` and `agent.py`
- The `agent.py` file must define a `root_agent` variable
- The `adk web` and `adk api_server` commands scan for these subdirectories

## Understanding ADK Commands

### `adk web` vs `adk api_server`

**Use `adk web .` for development and testing:**
- Includes the ADK Dev UI frontend (browser interface)
- Agent selection dropdown
- Chat interface with history
- Session management
- Perfect for testing and demos
- Default port: 8000 (local) or configurable with `--port`

**Use `adk api_server .` for production with custom frontends:**
- Backend API only, **NO built-in UI**
- Only use if you're building a custom frontend
- Returns 404 on `/` unless you have your own frontend
- Exposes REST API endpoints for agent communication

**In Docker (this project):**
- The Dockerfile uses `adk web` to provide the full UI experience
- Access at http://localhost:8080/ to see the frontend

## Extending the Agent

To add more cities or capabilities:

1. Update the `get_weather()` function with more cities
2. Add timezones to the `timezone_map` in `get_current_time()`
3. Create new tool functions and add them to the `tools` list in the Agent

## Troubleshooting

### Getting 404 errors when accessing the web UI?

**Problem:** Browser shows `{"detail":"Not Found"}` at http://localhost:8080/

**Solutions:**
1. **Check if you're using `adk web` (not `adk api_server`)**
   - `adk api_server` doesn't include the frontend UI
   - The Dockerfile should use: `CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080", "."]`

2. **Verify agent directory structure**
   - Your agent files MUST be in a subdirectory (e.g., `weather_agent/`)
   - NOT directly in the project root
   - Check that `weather_agent/__init__.py` and `weather_agent/agent.py` exist

3. **Rebuild the container with --no-cache**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Container keeps restarting?

Check the logs for errors:
```bash
docker-compose logs -f adk-agent
```

Common issues:
- Missing or invalid `GOOGLE_API_KEY` in `.env` file
- Python dependency conflicts (rebuild with `--no-cache`)

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Python GitHub](https://github.com/google/adk-python)
- [ADK Samples](https://github.com/google/adk-samples)
- [ADK API Server Documentation](https://google.github.io/adk-docs/runtime/api-server/)
