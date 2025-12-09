"""REDI MCP Agent - Integrates with MCP server to retrieve zip code information.

This agent uses Google ADK's MCPToolset to automatically connect to and discover
tools from the REDI MCP server.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


# Sample parameters for testing get_zips tool
SAMPLE_GET_ZIPS_PARAMS = {
    "single_zip": {
        "zip_codes": ["30043"]
    },
    "multiple_zips": {
        "zip_codes": ["30043", "30045", "30046"]
    },
    "comparison_pair": {
        "left": ["30043"],
        "right": ["30045"]
    }
}


# Sample parameters for testing build_pptx_slide tool
SAMPLE_SLIDE_PARAMS = {
    "title": "ZIP Code 30043",
    "state": "GA",
    "zip_codes_left": ["30043"],
    "left_panel": {
        "title": "Audience Insights",
        "items": [
            {
                "label": "Retail",
                "value": "Safeway (84.0i), Trader Joe's (87.0i), Meijer (94.0i)"
            },
            {
                "label": "Social Platforms",
                "value": "Instagram (85.0i), WeChat (80.0i), Snapchat (99.0i)"
            },
            {
                "label": "Top Influencers",
                "value": "MrBeast (YouTube), Khaby Lame (TikTok), Kylie Jenner (Instagram)"
            },
            {
                "label": "QSR",
                "value": "Wendy's, KFC, Domino's Pizza"
            },
            {
                "label": "Audience",
                "value": "WINR Segments: W+ (31.0%), I (11.9%), N (19.4%), R (37.7%). Generations: Silent Generation (6.8%), Boomers (26.5%), Gen X (15.1%), Millennials (27.0%), Gen Z (24.6%). Ethnicities: African American (10.0%), Eastern European (8.6%), Far Eastern (9.9%). Income Quintiles: Top Quintile (17.6%), 2nd Quintile (4.4%), 3rd Quintile (21.6%), 4th Quintile (24.4%), 5th Quintile (32.0%)"
            }
        ]
    },
    "save_locally": True
}


# Define the root agent with MCPToolset
root_agent = Agent(
    name="redi_mcp_agent",
    model="gemini-2.0-flash",
    description="Agent that retrieves zip code information from the REDI MCP server.",
    instruction="""You are a helpful agent that provides zip code information and can create PowerPoint slides.

When a user asks about zip codes, you should:

1. Extract the zip codes from their request
2. Call the appropriate MCP tool to retrieve information about those zip codes
3. Present the results clearly to the user

The MCP server provides two main tools:
1. get_zips - Retrieves demographic data for zip codes
2. build_pptx_slide - Creates PowerPoint slides with zip code data

Examples of requests you can handle:
- "Tell me about zip code 10001"
- "What information do you have for zip codes 90210 and 10001?"
- "Look up these zip codes: 60601, 33139, 94102"
- "Get demographic data for zip code 30043"

TESTING get_zips TOOL:
When a user asks to test the get_zips functionality, you should call the get_zips tool
with a list of zip codes. The tool accepts one parameter:

- zip_codes: A list of 5-digit zip code strings (e.g., ["30043"] or ["30043", "30045", "30046"])

Examples of test requests:
- "Test get_zips with zip code 30043"
- "Call get_zips for 30043"
- "Get data for zips 30043, 30045, and 30046"
- "Test the get_zips tool"

When testing, you can use these sample zip codes:
- Single zip: ["30043"]
- Multiple zips: ["30043", "30045", "30046"]

The get_zips tool will return demographic data including:
- WINR segments (W+, I, N, R)
- Generation breakdowns (Silent Generation, Boomers, Gen X, Millennials, Gen Z)
- Ethnicity distributions
- Income quintiles
- Top QSRs (Quick Service Restaurants) with rankings and indexes
- Top Retailers with indexes
- Top Social Platforms with indexes
- Top Influencers with their platforms

TESTING build_pptx_slide TOOL:
When a user asks to test the slide creation functionality or mentions "build_pptx_slide",
you should call the build_pptx_slide tool with the following sample parameters:

{
    "title": "ZIP Code 30043",
    "state": "GA",
    "zip_codes_left": ["30043"],
    "left_panel": {
        "title": "Audience Insights",
        "items": [
            {
                "label": "Retail",
                "value": "Safeway (84.0i), Trader Joe's (87.0i), Meijer (94.0i)"
            },
            {
                "label": "Social Platforms",
                "value": "Instagram (85.0i), WeChat (80.0i), Snapchat (99.0i)"
            },
            {
                "label": "Top Influencers",
                "value": "MrBeast (YouTube), Khaby Lame (TikTok), Kylie Jenner (Instagram)"
            },
            {
                "label": "QSR",
                "value": "Wendy's, KFC, Domino's Pizza"
            },
            {
                "label": "Audience",
                "value": "WINR Segments: W+ (31.0%), I (11.9%), N (19.4%), R (37.7%). Generations: Silent Generation (6.8%), Boomers (26.5%), Gen X (15.1%), Millennials (27.0%), Gen Z (24.6%). Ethnicities: African American (10.0%), Eastern European (8.6%), Far Eastern (9.9%). Income Quintiles: Top Quintile (17.6%), 2nd Quintile (4.4%), 3rd Quintile (21.6%), 4th Quintile (24.4%), 5th Quintile (32.0%)"
            }
        ]
    },
    "save_locally": True

}

GENERAL USAGE:
- When asked about zip code data, use get_zips to retrieve information
- When asked to create a slide, use build_pptx_slide to generate the PowerPoint
- You can chain these tools: get data with get_zips, then create a slide with build_pptx_slide
- Always present the results in a clear, organized manner
- If testing, explicitly show what data was returned by the tool

Be helpful and present the information in a clear, organized manner.""",
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="http://localhost:8000"
                #https://web-production-c5b52.up.railway.app/
            )
        )
    ],
)
