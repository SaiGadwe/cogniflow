import json
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context, Protocol
from agents.models.config import (
    RHYTHM_ADDRESS, SYNC_ADDRESS, INSIGHT_ADDRESS, ASI1_API_KEY,
)
from agents.models.models import SharedAgentState
from agents.services.state_service import state_service, PendingFanOut
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, EndSessionContent,
    TextContent, chat_protocol_spec,
)

chat_proto = Protocol(spec=chat_protocol_spec)

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

INTENT_PROMPT = """You are the intent classifier for CogniFlow, a cognitive study companion for neurodivergent students.

Classify the user's message into ONE of these intents:
- "study" — user wants help studying, preparing for an exam, or making a study plan
- "focus" — user wants to start or end a focus/pomodoro session
- "schedule" — user wants to see their calendar or free time
- "plan" — user wants to plan their day or routine
- "overwhelm" — user is struggling or shutting down
- "insight" — user wants to update their profile or preferences
- "status" — user wants an overview of today's progress

Return ONLY the intent word, nothing else."""


def classify_intent(query: str) -> str:
    try:
        if ASI1_API_KEY:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
            response = client.chat.completions.create(
                model="asi1-mini",
                messages=[
                    {"role": "system", "content": INTENT_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=10,
            )
            intent = response.choices[0].message.content.strip().lower().strip('"')
            valid = ("study", "focus", "schedule", "plan", "overwhelm", "insight", "status")
            if intent in valid:
                return intent
    except Exception:
        pass

    lower = query.lower()
    if any(kw in lower for kw in ["can't", "cannot", "too much", "overwhelm", "give up"]):
        return "overwhelm"
    if any(kw in lower for kw in ["study", "review", "exam", "midterm", "prepare", "help me"]):
        return "study"
    if any(kw in lower for kw in ["start focus", "focus session", "pomodoro", "timer"]):
        return "focus"
    if any(kw in lower for kw in ["end", "stop", "done", "finish"]):
        return "focus"
    if any(kw in lower for kw in ["schedule", "calendar", "free", "when am i"]):
        return "schedule"
    if any(kw in lower for kw in ["plan my day", "routine", "organize"]):
        return "plan"
    if any(kw in lower for kw in ["adhd", "dyslexia", "autism", "profile", "preference"]):
        return "insight"
    if any(kw in lower for kw in ["progress", "status", "overview"]):
        return "status"
    return "study"


# ---------------------------------------------------------------------------
# Chat message handler
# ---------------------------------------------------------------------------

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id
    ))

    text = " ".join(item.text for item in msg.content if isinstance(item, TextContent))
    ctx.logger.info(f"Received: {text}")

    chat_session_id = str(ctx.session)
    state = state_service.get_state(chat_session_id)

    if state is None:
        state = SharedAgentState(
            chat_session_id=chat_session_id,
            query=text,
            user_sender_address=sender,
            return_address=str(ctx.agent.address),
        )
        state_service.set_state(chat_session_id, state)
    else:
        state.query = text
        state.return_address = str(ctx.agent.address)
        state.chain_data = ""

    intent = classify_intent(text)
    ctx.logger.info(f"Intent: {intent}")

    if intent == "study":
        fanout = PendingFanOut(expected_agents=[SYNC_ADDRESS], query=text, user_sender=sender)
        fanout.intent = "study"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(INSIGHT_ADDRESS, state)

    elif intent == "focus":
        query_lower = text.lower()
        if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
            await ctx.send(RHYTHM_ADDRESS, state)
        else:
            fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS], query=text, user_sender=sender)
            fanout.intent = "focus"
            state_service.start_fanout(chat_session_id, fanout)
            await ctx.send(INSIGHT_ADDRESS, state)

    elif intent == "schedule":
        await ctx.send(SYNC_ADDRESS, state)

    elif intent == "overwhelm":
        fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS, INSIGHT_ADDRESS], query=text, user_sender=sender)
        fanout.intent = "overwhelm"
        state_service.start_fanout(chat_session_id, fanout)
        state_copy = SharedAgentState(chat_session_id=chat_session_id, query=text, user_sender_address=sender)
        await ctx.send(RHYTHM_ADDRESS, state_copy)
        await ctx.send(INSIGHT_ADDRESS, state_copy)

    elif intent == "insight":
        state.return_address = ""
        await ctx.send(INSIGHT_ADDRESS, state)

    elif intent == "status":
        fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS, SYNC_ADDRESS], query=text, user_sender=sender)
        fanout.intent = "status"
        state_service.start_fanout(chat_session_id, fanout)
        state_copy = SharedAgentState(chat_session_id=chat_session_id, query=text, user_sender_address=sender)
        await ctx.send(RHYTHM_ADDRESS, state_copy)
        await ctx.send(SYNC_ADDRESS, state_copy)

    else:
        await ctx.send(INSIGHT_ADDRESS, state)


@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

STUDY_PLAN_PROMPT = """You are CogniFlow, a cognitive study companion for neurodivergent students. Write a SHORT, warm study plan.

Format rules:
- Use markdown: **bold**, bullet points, ### headings
- Under 150 words total
- 2-3 bullet strategies max
- Do NOT list proposed time slots — UI shows those separately
- One motivating closing line
- Tone: {tone}

Student asked: {query}
Agent data: {data}"""

OVERWHELM_PROMPT = """You are CogniFlow. The student is overwhelmed. Be brief and compassionate (under 80 words).

- Acknowledge their feeling first
- Mention 1 accomplishment if focus stats show any
- Offer ONE tiny next step OR permission to stop

Student: {query}
Focus stats: {focus_data}
Profile: {insight_data}"""

SINGLE_FORMAT_PROMPT = """You are CogniFlow, a cognitive study companion. Format this into a concise, warm response.

Rules:
- Under 100 words
- Use markdown for structure
- End with one clear next action

Student: {query}
Data: {data}"""

PLAN_DAY_PROMPT = """You are CogniFlow. The student wants to plan their day.

Format rules:
- Under 150 words
- Use markdown with time blocks
- Explain WHY each time is recommended
- Tone: warm, practical

Student: {query}
Profile: {profile}
Calendar: {calendar}
Research: {research}"""


def format_with_llm(prompt: str, max_tokens: int = 800) -> str | None:
    if not ASI1_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
        response = client.chat.completions.create(
            model="asi1-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.5,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def generate_fanout_response(fanout: PendingFanOut) -> str:
    intent = getattr(fanout, "intent", "")

    if intent == "study":
        data = _safe_json(fanout.received.get(SYNC_ADDRESS, "{}"))
        advice = data.get("insight_advice", {})
        tone = advice.get("tone", "encouraging")
        prompt = STUDY_PLAN_PROMPT.format(tone=tone, query=fanout.query, data=json.dumps(data, indent=2))
        result = format_with_llm(prompt, max_tokens=1000)
        if result:
            return result
        slots = data.get("proposed_slots", [])
        return f"Study plan ready with {len(slots)} proposed time slots!"

    elif intent == "focus":
        data = _safe_json(fanout.received.get(RHYTHM_ADDRESS, "{}"))
        prompt = SINGLE_FORMAT_PROMPT.format(query=fanout.query, data=json.dumps(data, indent=2))
        return format_with_llm(prompt) or json.dumps(data, indent=2)

    elif intent == "overwhelm":
        focus_data = fanout.received.get(RHYTHM_ADDRESS, "{}")
        insight_data = fanout.received.get(INSIGHT_ADDRESS, "{}")
        prompt = OVERWHELM_PROMPT.format(query=fanout.query, focus_data=focus_data, insight_data=insight_data)
        return format_with_llm(prompt) or "Hey, I hear you. It's okay. Whatever you did today counts."

    elif intent == "status":
        all_data = {k: _safe_json(v) for k, v in fanout.received.items()}
        prompt = SINGLE_FORMAT_PROMPT.format(query=fanout.query, data=json.dumps(all_data, indent=2))
        return format_with_llm(prompt) or json.dumps(all_data, indent=2)

    all_data = {addr: data for addr, data in fanout.received.items()}
    prompt = SINGLE_FORMAT_PROMPT.format(query=fanout.query, data=json.dumps(all_data, indent=2))
    return format_with_llm(prompt) or json.dumps(all_data)


def generate_director_response_from_state(state: SharedAgentState) -> str:
    try:
        data = json.loads(state.result)
    except (json.JSONDecodeError, TypeError):
        return state.result or "I'm here. What would you like to work on?"

    if "error" in data:
        return f"Something went wrong: {data['error']}"

    prompt = SINGLE_FORMAT_PROMPT.format(query=state.query, data=json.dumps(data, indent=2))
    result = format_with_llm(prompt)
    if result:
        return result
    if "message" in data:
        return data["message"]
    return state.result