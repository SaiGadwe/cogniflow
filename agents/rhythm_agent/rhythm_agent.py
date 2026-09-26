import json

from agents.models.config import RHYTHM_SEED, ASI1_API_KEY, SYNC_ADDRESS
from agents.models.models import SharedAgentState
from agents.rhythm_agent.rhythm_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

rhythm_agent = Agent(
    name="cogniflow-rhythm",
    seed=RHYTHM_SEED,
    port=8002,
    mailbox=True,
    publish_agent_details=True,
)

if ASI1_API_KEY:
    mcp_adapter = MCPServerAdapter(mcp_server=mcp, asi1_api_key=ASI1_API_KEY, model="asi1-mini")
    for proto in mcp_adapter.protocols:
        rhythm_agent.include(proto, publish_manifest=True)


@rhythm_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received from {sender[:20]}...: query={state.query!r}")
    from agents.rhythm_agent.rhythm_mcp_server import (
        start_session, end_session, capture_thought, get_focus_stats,
    )

    query = state.query.lower()

    if state.chain_data:
        ctx.logger.info("Chain from Insight — building rhythm session plan")
        insight_data = json.loads(state.chain_data)
        advice = insight_data.get("advice", {})
        profile = insight_data.get("profile", {})

        duration = advice.get("recommended_session_length", profile.get("preferred_session_length", 15))
        break_len = advice.get("recommended_break_length", 5)
        strategies = advice.get("strategies", [])

        result_raw = start_session(duration, state.query)
        session_data = json.loads(result_raw)

        session_plan = {
            "session": session_data,
            "plan": {
                "duration_minutes": duration,
                "break_length": break_len,
                "strategies": strategies,
                "technique": strategies[0] if strategies else "Pomodoro",
                "task": state.query,
            },
            "insight_data": insight_data,
        }

        state.chain_data = json.dumps(session_plan)
        state.result = ""
        ctx.logger.info("Chaining: Rhythm → Sync")
        await ctx.send(SYNC_ADDRESS, state)
        return

    if any(kw in query for kw in ["end", "done", "stop", "finished"]):
        rating = 3
        for word in