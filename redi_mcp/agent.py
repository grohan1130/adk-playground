"""REDI MCP Agent - Integrates with MCP server to retrieve zip code information.

This agent uses Google ADK's MCPToolset to automatically connect to and discover
tools from the REDI MCP server.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


# Define the root agent with MCPToolset
root_agent = Agent(
    name="redi_mcp_agent",
    model="gemini-2.0-flash",
    description="Agent that retrieves zip code information from the REDI MCP server.",
    instruction="""You are a helpful agent that provides zip code information.

When a user asks about zip codes, you should:

1. Extract the zip codes from their request
2. Call the appropriate MCP tool to retrieve information about those zip codes
3. Present the results clearly to the user

The MCP server provides tools for looking up detailed information about zip codes.

Examples of requests you can handle:
- "Tell me about zip code 10001"
- "What information do you have for zip codes 90210 and 10001?"
- "Look up these zip codes: 60601, 33139, 94102"

Be helpful and present the information in a clear, organized manner.""",
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://web-production-c5b52.up.railway.app/"
            )
        )
    ],
)
