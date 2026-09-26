import json

from agents.models.config import INSIGHT_SEED, ASI1_API_KEY, RHYTHM_ADDRESS
from agents.models.models import SharedAgentState
from uagents import Agent, Context

insight_agent = Agent(
    name="cogniflow-insight",
    seed=INSIGHT_SEED,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

DEFAULT_PROFILE = {
    "disability_type": "ADHD",
    "preferred_session_length": 15,
    "reading_grade_level": 8,
    "chunk_size": "small",
    "tone": "encouraging",
    "scheduling_capacity": 0.65,
}


def _get_profile(ctx: Context) -> dict:
    raw = ctx.storage.get("profile")
    if raw:
        return json.loads(raw)
    ctx.storage.set("profile", json.dumps(DEFAULT_PROFILE))
    return dict(DEFAULT_PROFILE)


def _save_profile(ctx: Context, profile: dict):
    ctx.storage.set("profile", json.dumps(profile))


def _research_strategies(disability: str, context: str, profile: dict | None = None) -> dict:
    import re
    profile = profile or {}
    lower = context.lower()

    context_tag = ""
    if any(w in lower for w in ["exam", "midterm", "final", "test", "quiz"]):
        context_tag = "exam prep"
    elif any(w in lower for w in ["homework", "hw", "assignment"]):
        context_tag = "homework"
    elif any(w in lower for w in ["focus", "concentrate"]):
        context_tag = "focus"

    subject = ""
    subject_keywords = {
        "cs170": "data structures", "cs105": "computer science",
        "cs180": "artificial intelligence", "ai": "artificial intelligence",
        "data structures": "data structures", "algorithms": "algorithms",
        "calculus": "calculus", "physics": "physics",
        "machine learning": "machine learning",
    }
    for kw, subj in subject_keywords.items():
        if kw in lower:
            subject = subj
            break

    if not subject:
        cleaned = re.sub(
            r'(help me|can you|please|i need|i want|how do i|how to|study for|prepare for|my|the|a|an)\s*',
            '', lower,
        )
        words = [w for w in cleaned.split() if len(w) > 2]
        subject = " ".join(words[:3])

    parts = [disability, "student"]
    if subject:
        parts.append(subject)
    if context_tag:
        parts.append(context_tag)
    parts.append("study strategies")
    query = " ".join(parts)
    if len(query) > 80:
        query = query[:80].rsplit(" ", 1)[0]

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=3))
            sources = [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in raw_results
            ]
            return {"sources": sources, "query": query}
    except Exception as e:
        return {"sources": [], "query": query, "error": str(e)}


def _synthesize_advice(profile: dict, research: dict, user_query: str) -> dict:
    disability = profile.get("disability_type", "ADHD")
    sources_text = "\n".join(
        f"- {s['title']}: {s['snippet']}" for s in research.get("sources", [])
    )

    prompt = f"""You are a cognitive learning insight for a student with {disability}.
Based on this research, provide a concrete study strategy.

Research:
{sources_text}

Student's request: {user_query}

Return JSON with:
- "strategies": list of 3-4 specific techniques
- "recommended_session_length": integer minutes
- "recommended_break_length": integer minutes
- "advice": 2-3 sentence summary
- "key_insight": one important finding

Return ONLY valid JSON, no markdown."""

    try:
        if ASI1_API_KEY:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
            response = client.chat.completions.create(
                model="asi1-mini",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
    except Exception:
        pass

    return {
        "strategies": ["Pomodoro technique (15-min blocks)", "Active recall",
                       "Movement breaks every 45 min", "Study hardest material first"],
        "recommended_session_length": 15,
        "recommended_break_length": 5,
        "advice": f"Research shows {disability} students benefit from shorter focused sessions with regular breaks.",
        "key_insight": "Spaced repetition is more effective than cramming.",
    }


def _handle_profile_update(ctx: Context, query: str, profile: dict) -> dict:
    if "dyslexia" in query:
        profile["disability_type"] = "dyslexia"
        profile["preferred_session_length"] = 20
    elif "autism" in query or "asd" in query:
        profile["disability_type"] = "autism"
        profile["tone"] = "precise"
        profile["preferred_session_length"] = 25
    elif "adhd" in query:
        profile["disability_type"] = "ADHD"
        profile["tone"] = "encouraging"
        profile["preferred_session_length"] = 15
    _save_profile(ctx, profile)
    return profile


@insight_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    profile = _get_profile(ctx)
    query = state.query.lower()

    if any(kw in query for kw in ["update", "set", "change", "i have", "i am", "i'm"]):
        profile = _handle_profile_update(ctx, query, profile)

    disability = profile.get("disability_type", "ADHD")
    research = _research_strategies(disability, state.query, profile)
    advice = _synthesize_advice(profile, research, state.query)

    result = {
        "action": "insight_research",
        "profile": profile,
        "research": {"sources": research.get("sources", []), "search_query": research.get("query", "")},
        "advice": advice,
    }

    if state.return_address:
        ctx.logger.info("Chaining: Insight → Rhythm")
        state.chain_data = json.dumps(result)
        state.result = ""
        await ctx.send(RHYTHM_ADDRESS, state)
    else:
        state.result = json.dumps(result)
        await ctx.send(sender, state)


if __name__ == "__main__":
    insight_agent.run()