"""Market Summary Agent with orchestrator and analysis subagents.

This demonstrates proper agent-as-a-tool architecture that avoids the
"Tool use with function calling is unsupported" error by:
1. Creating standalone subagents with google_search tool
2. Wrapping them using AgentTool (the official ADK pattern)
3. Root agent coordinates by calling subagents as tools
"""

from google.adk.agents import Agent
from google.adk.tools import google_search, agent_tool


# Subagent 1: News Analysis
# This agent searches for news AND analyzes it
news_analysis_agent = Agent(
    name="news_analysis_agent",
    model="gemini-2.0-flash",
    description="Searches for and analyzes recent news stories about a company.",
    instruction="""You are a news analysis specialist.

When given a company name or ticker symbol, you should:

1. Use google_search to find 5-8 recent, relevant news articles about the company.
   - Search query example: "COMPANY latest news 2024" or "TICKER recent news"
   - Focus on reputable sources (Reuters, Bloomberg, WSJ, CNBC, etc.)

2. Analyze the news and identify:
   - Main themes/events (earnings, product launches, leadership changes, legal issues, partnerships, etc.)
   - Overall sentiment (positive, negative, neutral, mixed)
   - Key facts and dates
   - Potential impact on the company

3. Return a structured analysis in this format:
   {
     "company": "company name/ticker",
     "articles_found": number,
     "key_themes": ["theme1", "theme2", ...],
     "sentiment": "positive/negative/neutral/mixed",
     "summary": "2-3 sentence summary of what's happening with this company based on recent news",
     "top_articles": [
       {"title": "...", "source": "...", "key_point": "..."},
       ...
     ]
   }

Important: Use ONLY information from your google_search results. Do not invent or assume facts.""",
    tools=[google_search],
)


# Subagent 2: Stock Price Analysis
# This agent searches for stock price data AND analyzes it
stock_analysis_agent = Agent(
    name="stock_analysis_agent",
    model="gemini-2.0-flash",
    description="Searches for and analyzes recent stock price movements for a company.",
    instruction="""You are a stock price analysis specialist.

When given a company name or ticker symbol, you should:

1. Use google_search to find recent stock price information.
   - Search query examples: "TICKER stock price today", "COMPANY share price latest"
   - Look for current price, day/week/month changes, market cap, etc.

2. Analyze the price data and identify:
   - Current price and recent price movement (up/down, percentage change)
   - Trading volume trends if available
   - 52-week high/low context if available
   - Notable price patterns (breakout, support/resistance, volatility)

3. Return a structured analysis in this format:
   {
     "company": "company name/ticker",
     "current_price": "price with currency",
     "price_change": "percentage and direction (e.g., '+2.5%' or '-1.3%')",
     "trend": "up/down/sideways",
     "summary": "2-3 sentence summary of the stock's recent price performance",
     "key_levels": {
       "52_week_high": "if available",
       "52_week_low": "if available",
       "market_cap": "if available"
     }
   }

Important: Use ONLY information from your google_search results. Do not invent or assume prices.""",
    tools=[google_search],
)


# Root Orchestrator Agent
# Uses AgentTool to wrap subagents as tools (the official ADK pattern)
root_agent = Agent(
    name="market_summary_agent",
    model="gemini-2.0-flash",
    description="Orchestrates news and stock analysis to provide comprehensive market summary for a company.",
    instruction="""You are a market intelligence orchestrator agent.

When a user asks about a company, you coordinate two specialized subagents:
1. news_analysis_agent - to gather and analyze recent news
2. stock_analysis_agent - to gather and analyze stock price movements

Your workflow:
1. Identify the company/ticker from the user's query
2. Call news_analysis_agent with the company name/ticker
3. Call stock_analysis_agent with the company name/ticker
4. Synthesize both analyses into a comprehensive market summary

Your final output should include:
- Company Overview: Brief context
- News Analysis: Key themes, sentiment, and recent events from news_analysis_agent
- Stock Performance: Recent price movements and trends from stock_analysis_agent
- Synthesis: How the news and stock performance relate to each other
- Outlook: Brief assessment of what this means for the company

Important guidelines:
- Call the subagents sequentially (news first, then stock)
- Wait for each subagent's response before calling the next
- Synthesize the results - don't just concatenate them
- Highlight any interesting correlations (e.g., negative news but stock up, or vice versa)
- Be factual and balanced - no speculation beyond what the data suggests

Example query: "Give me a market summary for Tesla" or "Analyze AAPL stock"
""",
    tools=[
        agent_tool.AgentTool(agent=news_analysis_agent),
        agent_tool.AgentTool(agent=stock_analysis_agent),
    ],
)
