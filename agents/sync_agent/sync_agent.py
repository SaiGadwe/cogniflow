import json
from datetime import datetime, timedelta

from agents.models.config import SYNC_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from agents.sync_agent.sync_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

sync_agent = Agent(
    name="cogniflow-sync",
    seed=SYNC_SEED,
    port=8004,
    mailbox=True,
    publish_agent_details=True,
)

if ASI1_API_KEY:
    mcp_adapter = MCPServerAdapter(mcp_server=mcp, asi1_api_key=ASI1_API_KEY, model="asi1-mini")
    for proto in mcp_adapter.protocols:
        sync_agent.include(proto, publish_manifest=True)


def _pick_best_study_block(free_blocks: list[dict], min_duration: int = 30) -> dict | None:
    candidates = [b for b in free_blocks if b["duration_min"] >= min_duration]
    if not candidates:
        return None
    for b in candidates:
        hour = int(b["start"].split(":")[0])
        if 13 <= hour <= 17:
            return b
    for b in candidates:
        hour = int(b["start"].split(":")[0])
        if 9 <= hour <= 12:
            return b
    return candidates[0]


def _resolve_day_name(query: str, ref_date: datetime = None) -> str | None:
    if ref_date is None:
        ref_date = datetime.now()
    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    }
    lower = query.lower()
    if "today" in lower:
        return ref_date.strftime("%Y-%m-%d")
    if "tomorrow" in lower:
        return (ref_date + timedelta(days=1)).strftime("%Y-%m-%d")
    for name, weekday in sorted(day_map.items(), key=lambda x: -len(x[0])):
        if name in lower:
            days_ahead = (weekday - ref_date.weekday()) % 7 or 7
            return (ref_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return None


def _extract_date(query: str) -> str | None:
    import re
    match = re.search(r"\d{4}-\d{2}-\d{2}", query)
    return match.group(0) if match else None


@sync_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    from agents.sync_agent.sync_mcp_server import (
        get_events, get_free_blocks, get_upcoming_deadlines, create_event,
    )

    if state.chain_data:
        ctx.logger.info("Chain from Rhythm — finding study slots")
        chain = json.loads(state.chain_data)
        plan = chain.get("plan", {})
        insight_data = chain.get("insight_data", {})
        session = chain.get("session", {})

        duration = plan.get("duration_minutes", 15)
        task = plan.get("task", "Study session")
        strategies = plan.get("strategies", [])

        today = datetime.now()
        proposed_slots = []

        for i in range(1, 8):
            d = today + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            date_str = d.strftime("%Y-%m-%d")
            day_events = json.loads(get_events(date_str)).get("events", [])
            free = json.loads(get_free_blocks(date_str))
            best = _pick_best_study_block(free.get("free_blocks", []), duration)
            if not best:
                continue

            start = best["start"]
            sh, sm = map(int, start.split(":"))
            end_m = sm + duration
            end_h = sh + end_m // 60
            end_m = end_m % 60
            end_time = f"{end_h:02d}:{end_m:02d}"

            hour = int(start.split(":")[0])
            reason = ""
            for ev in day_events:
                ev_end_h, ev_end_m = map(int, ev["end"].split(":"))
                slot_start = hour * 60 + int(start.split(":")[1])
                if 0 <= (slot_start - (ev_end_h * 60 + ev_end_m)) <= 30:
                    reason = f"Right after {ev['title']} — review while fresh"
                    break
            if not reason:
                reason = "Morning gap — peak focus window" if 9 <= hour < 12 else f"Open slot on {d.strftime('%A')}"

            proposed_slots.append({
                "day": d.strftime("%A"),
                "date": date_str,
                "start": start,
                "end": end_time,
                "duration_min": duration,
                "reason": reason,
                "task": task[:40],
                "strategies": strategies[:2] if strategies else ["focused study"],
            })
            if len(proposed_slots) >= 3:
                break

        state.result = json.dumps({
            "action": "study_plan_proposed",
            "proposed_slots": proposed_slots,
            "session_plan": plan,
            "insight_research": insight_data.get("research", {}),
            "insight_advice": insight_data.get("advice", {}),
            "focus_session": session,
            "message": f"Found {len(proposed_slots)} study slots for you.",
        })

        target = state.return_address or sender
        await ctx.send(target, state)
        return

    query = state.query.lower()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    if any(kw in query for kw in ["free", "available", "open"]):
        date = _extract_date(query) or _resolve_day_name(query, today) or today_str
        state.result = get_free_blocks(date)
    elif any(kw in query for kw in ["deadline", "due", "upcoming"]):
        state.result = get_upcoming_deadlines(7)
    elif any(kw in query for kw in ["create", "add", "book"]):
        state.result = create_event("Study session", today_str, "15:00", "16:00", "Auto-scheduled by CogniFlow")
    else:
        date = _extract_date(query) or _resolve_day_name(query, today) or today_str
        state.result = get_events(date)

    await ctx.send(sender, state)


if __name__ == "__main__":
    sync_agent.run()