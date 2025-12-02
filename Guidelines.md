# Guidelines for Building Agents + Tools in Google ADK (or Similar Agent Frameworks)

## Why this matters  
- ADK’s runtime enforces **strict constraints** on how “agents” (LLM components) and “tools” (external APIs, search, etc.) can be combined. Violating those constraints leads to errors like `400 INVALID_ARGUMENT: Tool use with function calling is unsupported`. 
- Common pitfalls arise when trying to mix different “tool-mechanisms” (e.g. built-in search tools, function-declared tools, sub-agent orchestration) in the same agent/sub-agent hierarchy. 

---

## ✅ What you *should do* — correct patterns for agent + tool design

### RECOMMENDED: Using AgentTool for Modular Subagents with Tools

**AgentTool is the official ADK pattern** for building modular agent systems where subagents need their own tools. This approach solves the "Tool use with function calling is unsupported" error that occurs when trying to use subagents with built-in tools directly.

**How AgentTool works:**
- Create standalone subagents, each with their own tools (like `google_search`)
- Wrap each subagent using `AgentTool`
- Assign the wrapped subagents to the root agent's `tools` list (NOT `sub_agents`)
- Root agent orchestrates by calling subagents as if they were tools

**Python Example:**

```python
from google.adk.agents import Agent
from google.adk.tools import google_search, agent_tool

# Create subagents with their own tools
news_agent = Agent(
    name="news_analysis_agent",
    model="gemini-2.0-flash",
    description="Searches for and analyzes news",
    instruction="Use google_search to find news, then analyze...",
    tools=[google_search],  # Subagent has its own tools
)

stock_agent = Agent(
    name="stock_analysis_agent",
    model="gemini-2.0-flash",
    description="Searches for and analyzes stock data",
    instruction="Use google_search to find stock info, then analyze...",
    tools=[google_search],  # Subagent has its own tools
)

# Root agent uses AgentTool to wrap subagents
root_agent = Agent(
    name="market_summary_agent",
    model="gemini-2.0-flash",
    description="Orchestrates news and stock analysis",
    instruction="Call news_analysis_agent and stock_analysis_agent, then synthesize...",
    tools=[
        agent_tool.AgentTool(agent=news_agent),    # Wrapped as tool
        agent_tool.AgentTool(agent=stock_agent),   # Wrapped as tool
    ],
)
```

**Visual Builder / YAML Approach:**

You can also define agents using YAML configuration files and reference them via `config_path`:

```yaml
name: demo_news_agg
model: gemini-2.5-flash
agent_class: LlmAgent
instruction: You are the root agent that coordinates other agents.
tools:
  - name: AgentTool
    args:
      agent:
        config_path: ./headline_getter.yaml
      skip_summarization: false
  - name: AgentTool
    args:
      agent:
        config_path: ./stockprice_getter.yaml
      skip_summarization: false
```

**Key benefits:**
- ✅ Proper separation of concerns (each subagent focuses on one capability)
- ✅ Subagents can use built-in tools without triggering errors
- ✅ Reusable subagents across different root agents
- ✅ Clear orchestration pattern that follows ADK's architecture

---

### Alternative Patterns (for simpler cases)

1. **For simple single-agent scenarios: assign tools directly to the agent.**
   - If you don't need modularity or subagent orchestration, just assign tools directly to your root agent.
   - Example: `root_agent = Agent(name="...", tools=[google_search, custom_tool])`
   - This is the simplest pattern but doesn't provide modularity or reusability.

2. **IMPORTANT: Don't use `sub_agents` parameter for agents that have tools.**
   - The `sub_agents=[...]` parameter causes the "Tool use with function calling is unsupported" error when subagents use tools.
   - **Solution: Use AgentTool instead** (see recommended pattern above) - wrap subagents and assign to the `tools` list, not `sub_agents`.
   - AgentTool was specifically designed to solve this limitation.

3. **Root agent should orchestrate; all tool calls happen at the top level.**
   - Whether using AgentTool-wrapped subagents or direct tools, the root agent coordinates everything.
   - Pattern: root agent → call tool/subagent → receive response → aggregate → output
   - When using AgentTool, the root agent calls subagents as if they were tools, and those subagents internally use their own tools.  

4. **Keep agents focused: "one agent, one concern" when possible.**
   - AgentTool enables proper modularity: each subagent handles one specific capability.
   - Each wrapped subagent can be reused across different root agents.
   - Avoid over-complex nested hierarchies beyond root → AgentTool-wrapped subagents.  

5. **Test incrementally.**  
   - First test each tool individually (e.g. test that the search tool returns sensible results; test the weather tool works).  
   - Then integrate into one agent that calls them both — avoids confusion about which part failed (tool vs orchestration).  

---

## ⚠️ Why "the naive / intuitive" approach often fails (and what we learnt)

- It feels natural to design a modular system: a root orchestrator + sub-agents each specialized (e.g. news agent, weather agent). But under ADK, when using `sub_agents=[...]` parameter, if a sub-agent uses a built-in tool, the switch from "function-call activation" → "tool invocation" is not supported — hence the 400 error.
- **AgentTool was created to solve this exact problem**: it wraps agents so they can be assigned to the `tools` list instead of `sub_agents`, which enables proper tool usage within subagents.
- Without AgentTool, attempting to use `sub_agents` with tools leads to brittle designs, unexpected errors, or infinite loops in multi-agent coordination. 

---

## Mental Model / How to "Think About" Agents vs Tools (for ADK or similar frameworks)

- **Agent = "thinker / orchestrator / decision-maker"** — the LLM brain that reasons, plans, aggregates results, and outputs final answers.
- **Tool = "external capability / action / API call"** — something outside the LLM that does real work (searching web, fetching weather, running code, etc.).
- **AgentTool = "wrapper that makes agents behave like tools"** — bridges the gap between agent orchestration and tool usage. It wraps a subagent so the root agent can call it as if it were a tool, while the subagent internally uses its own tools.
- **Key insight**: The `sub_agents` parameter doesn't support tool usage within subagents, but AgentTool (assigned to `tools` list) does.
- **Recommended approach**: Root agent has `tools=[AgentTool(subagent1), AgentTool(subagent2)]`, where each subagent has its own `tools=[google_search, ...]`

---

## 🧑‍💻 Recommended Template for Building a Multi-Capability Agent

> *Use this template when instructing an AI-assistant or writing code — it follows ADK's constraints correctly*:

### Template Option 1: AgentTool Pattern (Recommended for Modularity)

```text
- Define specialized subagents, each with their own tools:
  - news_agent with tools=[google_search]
  - weather_agent with tools=[google_search] or custom weather API
  - Each subagent has focused instructions for its specific task

- Define root orchestrator agent:
  - Name: "daily_update_agent" (or similar)
  - Assign tools = [AgentTool(news_agent), AgentTool(weather_agent)]
  - Do NOT assign sub_agents parameter
  - In root agent instruction:
      1. Call news_agent tool to fetch and analyze news
      2. Call weather_agent tool to get forecast
      3. Synthesize both results into final output

- Key points:
  - Import: from google.adk.tools import agent_tool
  - Wrap: agent_tool.AgentTool(agent=subagent)
  - Assign wrapped agents to tools list, NOT sub_agents
  - Each subagent can have its own tools without conflicts
```

### Template Option 2: Simple Direct Tools (For Non-Modular Cases)

```text
- Define custom tool functions: search_tool, weather_tool, etc.
- Define one root agent: "simple_agent"
  - Assign tools = [search_tool, weather_tool, ...]
  - Do NOT assign sub_agents
  - In agent instruction:
      1. Call tool "search_tool" to fetch data
      2. Call tool "weather_tool" to get forecast
      3. Combine results into final output

- Use this approach when:
  - You don't need modularity or reusable subagents
  - The logic is simple enough for one agent
  - You want the simplest possible implementation
```

