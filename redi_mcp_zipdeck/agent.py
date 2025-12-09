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
    #url="https://web-production-c5b52.up.railway.app/"
    url="http://localhost:8000/"
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
   - Keywords: "compare", "comparing", "difference between"
   - Patterns: "X and Y vs Z", "compare X with Y", "comparing X and Y"

3. Group zip codes (CRITICAL - read carefully):
   - If "vs/versus" found: Split at that point
     Example: "30045, 30043 vs 30046, 30047" → left=["30045", "30043"], right=["30046", "30047"]
   - If "compare/comparing X with/to/and Y" where X and Y are individual zips: 1v1 comparison
     Example: "compare 30045 with 30046" → left=["30045"], right=["30046"]
     Example: "comparing 30043 and 30045" → left=["30043"], right=["30045"]
   - If "compare X, Y with Z, W" (multiple zips in each group): Set comparison
     Example: "compare 30045, 30043 with 30046, 30047" → left=["30045", "30043"], right=["30046", "30047"]
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

User: "comparing 30043 and 30045"
Output: {
  "comparison_type": "comparison",
  "left_zips": ["30043"],
  "right_zips": ["30045"],
  "original_query": "comparing 30043 and 30045"
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
- "comparing A and B" = comparison with left=[A], right=[B] (NOT aggregate!)
- "compare A, B with C, D" = comparison with left=[A,B], right=[C,D]
- Only use aggregate for multiple zips WITHOUT comparison keywords
- Be flexible with natural language patterns""",
    tools=[],  # No tools - pure text analysis
)


# Step 1: ZipDataRetriever
# Calls get_zips (once or twice based on query_structure) and returns raw demographic data
zip_data_retriever = Agent(
    name="zip_data_retriever",
    model="gemini-2.0-flash",
    description="Retrieves demographic data for zip codes using the get_zips MCP tool.",
    output_key="zip_data",  # Capture get_zips output for next step
    instruction="""YOU ARE A TOOL EXECUTION BOT. YOU HAVE NO DATA. YOU ONLY CALL TOOLS.

INPUT: query_structure object with left_zips and right_zips fields.

YOUR FIRST ACTION: Call the get_zips tool. DO NOT OUTPUT TEXT FIRST.

EXECUTION SEQUENCE (DO NOT SKIP ANY STEP):

STEP 1: Call get_zips tool with left_zips
  - Read query_structure.left_zips
  - IMMEDIATELY call: get_zips(zip_codes=<value of left_zips>)
  - Wait for tool response containing demographic data

STEP 2: If right_zips exists, call get_zips tool again
  - Read query_structure.right_zips
  - If not null: IMMEDIATELY call: get_zips(zip_codes=<value of right_zips>)
  - Wait for tool response containing demographic data

STEP 3: Format the tool responses
  - Take the RAW tool outputs from STEP 1 and STEP 2
  - Return: {"left_data": <tool_output_1>, "right_data": <tool_output_2_or_null>}

CRITICAL CONSTRAINTS:
- You CANNOT generate output until AFTER you have called get_zips and received responses
- Your output MUST contain fields like "top_qsrs", "demographics", "top_retailers" from the tool
- If your output only contains zip codes like {"left_zips": [...], "right_zips": [...]}, YOU FAILED
- Do NOT write explanatory text - ONLY call tools and return their outputs

VERIFICATION:
- Did you call the get_zips tool? If NO, STOP and call it now.
- Does your output contain demographic data from the tool? If NO, you did it wrong.
- Does your output have "left_data" and "right_data" keys? If NO, fix the format.

FORBIDDEN:
- Do NOT return anything before calling get_zips
- Do NOT echo back the input zips
- Do NOT hallucinate data
- Do NOT skip tool execution""",
    tools=[MCPToolset(connection_params=MCP_CONNECTION)],
)


# Step 2: DataFormatter
# Transforms raw get_zips data into slide parameters
data_formatter = Agent(
    name="data_formatter",
    model="gemini-2.0-flash",
    description="Transforms raw zip code data into formatted slide parameters for build_pptx_slide.",
    output_key="slide_params",  # Capture formatted parameters for next step
    instruction="""You are a data formatting specialist. Transform raw data into slide parameters.

INPUT:
1. query_structure: Contains comparison_type, left_zips, right_zips
2. zip_data: Contains raw tool outputs with left_data and right_data

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
- Look at the first zip code in `left_zips`
- Use your internal general knowledge to determine which US State that zip code belongs to
- Examples: 30045 → "GA", 10001 → "NY", 90210 → "CA", 60601 → "IL"
- Set the "state" field to the 2-letter state abbreviation

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
- State: AUTO-INFER from first zip code using internal knowledge (no lookup needed)
- Left/right panels: Use title+items format {"title": "...", "items": [...]}
- Bottom panel: Use title+text format {"title": "...", "text": "..."}
- Panel titles MUST show specific zip codes: "ZIP Code 30045 Insights" or "ZIP Codes 30045, 30043 Insights"
- Extract data from left_data for left_panel, right_data for right_panel
- Use ACTUAL values from tool outputs, not placeholders
- COMMA-separated values (not pipes)
- Do NOT call any tools - just format the data received
- Always include bottom_panel with strategic recommendations
- For comparisons, MUST include both left and right panels

OUTPUT: Valid JSON/dictionary ready for build_pptx_slide.""",
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
