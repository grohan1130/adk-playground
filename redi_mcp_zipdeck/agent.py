"""REDI MCP ZipDeck Agent - Sequential workflow for deterministic data flow.

This agent uses SequentialAgent with explicit output_key to ensure deterministic
data passing between steps, eliminating LLM reasoning gaps:

1. query_analyzer: Parses user intent and groups zip codes → output_key="query_structure"
2. zip_data_retriever: Calls get_zips (once or twice) → output_key="zip_data"
3. data_formatter: Transforms zip_data into panel format → output_key="slide_params"
4. slide_builder: Calls build_pptx_slide with slide_params

Architecture:
- SequentialAgent with 4 explicit steps
- output_key captures each step's output deterministically
- No LLM reasoning required for data transformation
- Clear, debuggable data flow
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


# MCP Server Connection Parameters
MCP_CONNECTION = StreamableHTTPConnectionParams(
    url="https://web-production-c5b52.up.railway.app/"
)


# Step 0: QueryAnalyzer
# Parses user intent and groups zip codes for comparison
query_analyzer = Agent(
    name="query_analyzer",
    model="gemini-2.0-flash",
    description="Analyzes user query to determine comparison type and group zip codes.",
    output_key="query_structure",  # Captures query structure for next steps
    instruction="""You are a query analysis specialist.

Your ONLY job is to parse the user's query and determine:
1. What type of request is it?
2. Which zip codes belong to which group?

QUERY TYPES:
- "single": One zip code
- "aggregate": Multiple zips to be treated as one group
- "comparison": Comparing two groups (1v1, 1vMany, ManyVMany)

PARSING RULES:

1. Extract all zip codes from the query (5-digit numbers)

2. Detect comparison intent using:
   - Explicit separators: "vs", "versus", "compared to", "compared with"
   - Keywords: "compare", "difference between"
   - Patterns: "X and Y vs Z" or "compare X with Y"

3. Group zip codes:
   - If "vs/versus" found: Split at that point
     Example: "30045, 30043 vs 30046, 30047" → left=["30045", "30043"], right=["30046", "30047"]
   - If "compare X with/to Y": First group = X, second group = Y
     Example: "compare 30045 with 30046, 30047" → left=["30045"], right=["30046", "30047"]
   - If multiple zips but NO comparison keywords: type="aggregate"
   - If single zip: type="single"

OUTPUT FORMAT (JSON/dict):
{
  "comparison_type": "single" | "aggregate" | "comparison",
  "left_zips": ["XXXXX", ...],    # Always present
  "right_zips": ["YYYYY", ...],   # Only for comparison type
  "original_query": "user's original text"
}

EXAMPLES:

User: "Show me a slide for zip code 30045"
Output: {
  "comparison_type": "single",
  "left_zips": ["30045"],
  "right_zips": null,
  "original_query": "Show me a slide for zip code 30045"
}

User: "Create a slide for 30045, 30043, 30046"
Output: {
  "comparison_type": "aggregate",
  "left_zips": ["30045", "30043", "30046"],
  "right_zips": null,
  "original_query": "Create a slide for 30045, 30043, 30046"
}

User: "Compare 30045 with 30046"
Output: {
  "comparison_type": "comparison",
  "left_zips": ["30045"],
  "right_zips": ["30046"],
  "original_query": "Compare 30045 with 30046"
}

User: "30045, 30043 vs 30046, 30047"
Output: {
  "comparison_type": "comparison",
  "left_zips": ["30045", "30043"],
  "right_zips": ["30046", "30047"],
  "original_query": "30045, 30043 vs 30046, 30047"
}

User: "compare zip codes 30045 and 30043 with 30046 and 30047"
Output: {
  "comparison_type": "comparison",
  "left_zips": ["30045", "30043"],
  "right_zips": ["30046", "30047"],
  "original_query": "compare zip codes 30045 and 30043 with 30046 and 30047"
}

CRITICAL:
- Return VALID JSON/dict format
- Include all required fields
- Use null (not empty list) for right_zips when not a comparison
- Extract ALL zip codes from the query
- Be flexible with natural language patterns
- Default to "aggregate" if multiple zips but unclear intent""",
    tools=[],  # No tools - pure text analysis
)


# Step 1: ZipDataRetriever
# Calls get_zips (once or twice based on query_structure) and returns raw demographic data
zip_data_retriever = Agent(
    name="zip_data_retriever",
    model="gemini-2.0-flash",
    description="Retrieves demographic data for zip codes using the get_zips MCP tool.",
    output_key="zip_data",  # Capture get_zips output for next step
    instruction="""You are a zip code data retrieval specialist.

Your ONLY job is to call the get_zips tool a number of times based on the query_structure and return the complete output.

INPUT: You receive a query_structure dictionary containing:
- comparison_type: "single", "aggregate", or "comparison"
- left_zips: List of zip codes for the left/primary group
- right_zips: List of zip codes for the right group (null if not a comparison)

ACTIONS BASED ON COMPARISON TYPE:

1. FOR "single" OR "aggregate":
   - Call get_zips(zip_codes=left_zips)
   - Return: {"left_data": <complete get_zips response>, "right_data": null}

2. FOR "comparison":
   - Call get_zips(zip_codes=left_zips) → Store as left_data
   - Call get_zips(zip_codes=right_zips) again → Store as right_data
   - Return: {"left_data": <response 1>, "right_data": <response 2>}

The get_zips tool returns demographic data including:
- WINR segments
- Generation breakdowns
- Ethnicity distributions
- Income quintiles
- Top QSRs (Quick Service Restaurants) with rankings
- Top Retailers with rankings
- Top Social Platforms with rankings
- Top Influencers with rankings

OUTPUT FORMAT:
{
  "left_data": <complete get_zips response for left_zips>,
  "right_data": <complete get_zips response for right_zips OR null>
}

EXAMPLES:

Input: {"comparison_type": "single", "left_zips": ["30045"], "right_zips": null}
Action: Call get_zips(zip_codes=["30045"])
Output: {"left_data": <response>, "right_data": null}

Input: {"comparison_type": "comparison", "left_zips": ["30045", "30043"], "right_zips": ["30046", "30047"]}
Action: Call get_zips(zip_codes=["30045", "30043"])
        Call get_zips(zip_codes=["30046", "30047"])
Output: {"left_data": <response 1>, "right_data": <response 2>}

CRITICAL:
- Make TWO separate get_zips calls for comparisons
- Return COMPLETE unmodified responses from get_zips
- Always return the {"left_data": ..., "right_data": ...} format
- Do NOT summarize or filter the data""",
    tools=[MCPToolset(connection_params=MCP_CONNECTION)],
)


# Step 2: DataFormatter
# Transforms raw get_zips data into slide parameters
data_formatter = Agent(
    name="data_formatter",
    model="gemini-2.0-flash",
    description="Transforms raw zip code data into formatted slide parameters for build_pptx_slide.",
    output_key="slide_params",  # Capture formatted parameters for next step
    instruction="""You are a data formatting specialist for PowerPoint slides.

Your ONLY job is to transform the raw get_zips data into the exact parameter format needed by build_pptx_slide.

INPUT: You receive TWO pieces of information:
1. query_structure: Contains comparison_type, left_zips, right_zips
2. zip_data: Contains {"left_data": <data>, "right_data": <data or null>}

OUTPUT: You must create a dictionary with these parameters:

SINGLE ZIP CODE:
{
  "title": "ZIP Code XXXXX",
  "state": "XX",
  "zip_codes_left": ["XXXXX"],
  "left_panel": {
    "title": "ZIP Code XXXXX Insights",
    "items": [
      {"label": "Retail", "value": "Store1 (84.0i), Store2 (87.0i), Store3 (94.0i)"},
      {"label": "Social Platforms", "value": "Platform1 (85.0i), Platform2 (80.0i)"},
      {"label": "Top Influencers", "value": "Name1 (Platform), Name2 (Platform)"},
      {"label": "QSR", "value": "Restaurant1, Restaurant2, Restaurant3"},
      {"label": "Audience", "value": "Demographics summary text"}
    ]
  },
  "bottom_panel": {
    "title": "Strategic Recommendations",
    "text": "Based on the data, here are key recommendations:\n• Partner with high-index retailers like Store1 (84.0i) for targeted promotions\n• Leverage Platform1 (85.0i) for social media campaigns\n• Focus on Demographics audience segment for maximum engagement"
  }
}

COMPARISON (1 ZIP VS 1 ZIP OR SET VS SET):
{
  "title": "ZIP Code XXXXX vs YYYYY",
  "state": "XX",
  "zip_codes_left": ["XXXXX"],
  "left_panel": {
    "title": "ZIP Code XXXXX Insights",
    "items": [...]
  },
  "zip_codes_right": ["YYYYY"],
  "right_panel": {
    "title": "ZIP Code YYYYY Insights",
    "items": [...]
  },
  "bottom_panel": {
    "title": "Comparison Insights",
    "text": "Key differences and opportunities:\n• Left area shows higher affinity for Retail1 (97.0i) vs Right area Retail2 (84.0i)\n• Demographics differ: Left skews Gen Z (35%) while Right is more Millennial (40%)\n• Recommend tailored campaigns per area based on these distinct profiles"
  }
}

PANEL FORMATTING RULES:

LEFT/RIGHT PANELS (for demographic data):
1. MUST use {"title": "...", "items": [...]} format
2. Each item in "items" must be {"label": "...", "value": "..."}
3. Title should show specific zip codes: "ZIP Code 30045 Insights" or "ZIP Codes 30045, 30043 Insights"
4. Extract ACTUAL DATA from get_zips (no placeholders)
5. Values should be COMMA-SEPARATED lists (NOT pipe-separated)
6. Format each section:
   - Retail: "Store1 (84.0i), Store2 (87.0i), Store3 (94.0i)"
   - Social Platforms: "Platform1 (85.0i), Platform2 (80.0i)"
   - Top Influencers: "Name1 (Platform), Name2 (Platform)"
   - QSR: "Restaurant1, Restaurant2, Restaurant3"
   - Audience: "WINR Segments: W+ (31%), I (12%). Generations: Boomers (26%), Gen Z (25%)"

BOTTOM PANEL (for recommendations/summary):
1. MUST use {"title": "...", "text": "..."} format
2. NO items list - only "title" and "text" fields
3. "text" is a SINGLE STRING with bullet points formatted using \n• for line breaks
4. Example: "Key insights:\n• Point 1\n• Point 2\n• Point 3"
5. Lists or nested dictionaries are NOT supported

FORMATTING LOGIC BASED ON comparison_type:

1. FOR "single" OR "aggregate":
   - Use left_data to populate left_panel
   - Use left_zips for zip_codes_left
   - left_panel title: "ZIP Code XXXXX Insights" (single) or "ZIP Codes XXXXX, YYYYY Insights" (aggregate)
   - Do NOT include zip_codes_right or right_panel
   - Slide title: "ZIP Code XXXXX" (single) or "ZIP Codes XXXXX, YYYYY, ZZZZZ" (aggregate)
   - bottom_panel: Strategic recommendations as text string

2. FOR "comparison":
   - Use left_data to populate left_panel
   - Use right_data to populate right_panel
   - Use left_zips for zip_codes_left, right_zips for zip_codes_right
   - left_panel title: "ZIP Code(s) XXXXX Insights" (show specific zips)
   - right_panel title: "ZIP Code(s) YYYYY Insights" (show specific zips)
   - Slide title: "ZIP Code(s) XXXXX vs YYYYY" (show all zips in each set)
   - bottom_panel: Comparison insights as text string

EXTRACTION EXAMPLE:
If left_zips = ["30045"] and get_zips returns:
{
  "top_qsrs": [
    {"name": "Wendy's", "rank": 1, "index": 95.5},
    {"name": "Domino's Pizza", "rank": 2, "index": 88.3}
  ],
  "top_retailers": [
    {"name": "Safeway", "index": 97.0},
    {"name": "Meijer", "index": 107.0}
  ],
  "demographics": {...}
}

Format as:
{
  "left_panel": {
    "title": "ZIP Code 30045 Insights",
    "items": [
      {"label": "QSR", "value": "Wendy's, Domino's Pizza"},
      {"label": "Retail", "value": "Safeway (97.0i), Meijer (107.0i)"},
      ...
    ]
  }
}

BOTTOM PANEL RECOMMENDATIONS:
Generate 2-4 strategic marketing recommendations as a SINGLE TEXT STRING:
- Format with bullet points using \n• for line breaks
- Identify unique opportunities (high-index retailers/platforms)
- Suggest target audiences based on demographics
- Recommend channels or partners for engagement
- For comparisons, highlight key differences and opportunities

Example text format:
"Strategic recommendations based on analysis:\n• Partner with Safeway (97.0i) for in-store promotions\n• Target Gen Z (35%) audience with social media campaigns\n• Leverage Instagram (92.0i) as primary platform\n• Consider influencer partnerships with top local personalities"

STATE INFERENCE:
- 30000-31999 → "GA" | 10000-14999 → "NY" | 90000-96699 → "CA"
- Infer from first zip code

FULL EXAMPLE FOR COMPARISON:

Input query_structure:
{
  "comparison_type": "comparison",
  "left_zips": ["30045", "30043"],
  "right_zips": ["30046", "30047"]
}

Input zip_data:
{
  "left_data": {<get_zips response for 30045, 30043>},
  "right_data": {<get_zips response for 30046, 30047>}
}

Output slide_params:
{
  "title": "ZIP Codes 30045, 30043 vs 30046, 30047",
  "state": "GA",
  "zip_codes_left": ["30045", "30043"],
  "left_panel": {
    "title": "ZIP Codes 30045, 30043 Insights",
    "items": [<extracted from left_data>]
  },
  "zip_codes_right": ["30046", "30047"],
  "right_panel": {
    "title": "ZIP Codes 30046, 30047 Insights",
    "items": [<extracted from right_data>]
  },
  "bottom_panel": {
    "title": "Comparison Insights",
    "text": "Key differences and strategic opportunities:\n• Left area (30045, 30043) shows higher retail engagement with Kroger (105.0i) vs Right area (30046, 30047) Publix (88.0i)\n• Demographics: Left skews younger Gen Z (32%) while Right is more Millennial-focused (38%)\n• Social platform preferences differ: Left favors TikTok (95.0i) vs Right prefers Instagram (90.0i)\n• Recommend geo-targeted campaigns with platform-specific creative tailored to each area's demographics"
  }
}

CRITICAL:
- Left/right panels: Use title+items format {"title": "...", "items": [...]}
- Bottom panel: Use title+text format {"title": "...", "text": "..."}
- Panel titles MUST show specific zip codes: "ZIP Code 30045 Insights" or "ZIP Codes 30045, 30043 Insights"
- Extract data from left_data for left_panel
- Extract data from right_data for right_panel (if comparison)
- Use ACTUAL values, not placeholders
- COMMA-separated values (not pipes)
- Do NOT call any tools - just format the data
- Always include bottom_panel with strategic recommendations as text string
- For comparisons, MUST include both left and right panels with their respective data

OUTPUT FORMAT: Return valid JSON/dictionary ready for build_pptx_slide.""",
    tools=[],  # No tools - pure data transformation
)


# Step 3: SlideBuilder
# Calls build_pptx_slide with formatted parameters
slide_builder = Agent(
    name="slide_builder",
    model="gemini-2.0-flash",
    description="Creates PowerPoint slides using the build_pptx_slide MCP tool.",
    instruction="""You are a PowerPoint slide creation specialist.

Your ONLY job is to call build_pptx_slide with the parameters provided to you.

INPUT: You receive a dictionary containing:
- title: Slide title (required)
- state: State abbreviation (required)
- zip_codes_left: List of zip codes for left panel (required)
- left_panel: Dictionary with title+items format (required)
- zip_codes_right: List of zip codes for right panel (optional - for comparisons)
- right_panel: Dictionary with title+items format (optional - for comparisons)
- bottom_panel: Dictionary with title+text format (optional - for recommendations)

ACTION:
1. Call build_pptx_slide with these EXACT parameters
2. Pass ALL provided parameters (including optional ones if present)
3. Wait for the response containing the slide URL
4. Return the slide URL to the user

CRITICAL:
- Use the parameters EXACTLY as provided - do NOT modify them
- Left/right panels use title+items format
- Bottom panel uses title+text format
- Do NOT reformat or change the panel structure
- Include all optional parameters if they exist in the input

Example (Single Zip):
Input: {
  "title": "ZIP Code 30045",
  "state": "GA",
  "zip_codes_left": ["30045"],
  "left_panel": {
    "title": "ZIP Code 30045 Insights",
    "items": [{"label": "Retail", "value": "..."}, ...]
  },
  "bottom_panel": {
    "title": "Strategic Recommendations",
    "text": "Strategic insights:\n• Partner with high-index retailers\n• Target Gen Z demographic"
  }
}

Action: Call build_pptx_slide(
  title="ZIP Code 30045",
  state="GA",
  zip_codes_left=["30045"],
  left_panel={...},
  bottom_panel={...}
)

Example (Comparison):
Input: {
  "title": "ZIP Code 30045 vs 30043",
  "state": "GA",
  "zip_codes_left": ["30045"],
  "left_panel": {
    "title": "ZIP Code 30045 Insights",
    "items": [...]
  },
  "zip_codes_right": ["30043"],
  "right_panel": {
    "title": "ZIP Code 30043 Insights",
    "items": [...]
  },
  "bottom_panel": {
    "title": "Comparison Insights",
    "text": "Key differences:\n• Left area higher retail engagement\n• Right area more Millennial-focused"
  }
}

Action: Call build_pptx_slide with ALL parameters including right_panel

Output: "Slide created! URL: [URL]" """,
    tools=[MCPToolset(connection_params=MCP_CONNECTION)],
)


# Root Agent: SequentialAgent with 4 sub-agents
# SequentialAgent is deterministic (not LLM-powered) and executes sub-agents in order
# Data flows via output_key: query_analyzer → zip_data_retriever → data_formatter → slide_builder
root_agent = SequentialAgent(
    name="redi_mcp_sequential_agent",
    sub_agents=[
        query_analyzer,      # output_key="query_structure"
        zip_data_retriever,  # output_key="zip_data"
        data_formatter,      # output_key="slide_params"
        slide_builder        # uses slide_params from previous step
    ]

)
