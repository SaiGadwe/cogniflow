import json
from datetime import datetime, timezone
from uuid import uuid4

from agents.models.config import DIRECTOR_SEED, INSIGHT_ADDRESS, RHYTHM_ADDRESS, SYNC_ADDRESS
from agents.models.models import SharedAgentState
from agents.director_agent.chat_protocol import (
    chat_proto, classify_intent, generate_director_response_from_state,
    generate_fanout_response,
)
from agents.services.state_service import state_service, PendingFanOut
from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import ChatMessage, EndSessionContent, TextContent

director = Agent(
    name="cogniflow-director",
    seed=DIRECTOR_SEED,
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)

director.include(chat_proto, publish_manifest=True)

_completed: dict[str, dict] = {}


class HealthResponse(Model):
    status: str

class HttpMessagePost(Model):
    content: str

class HttpMessageResponse(Model):
    session_id: str
    intent: str

class HttpResultRequest(Model):
    session_id: str

class HttpResultResponse(Model):
    ready: bool
    response: str
    raw_data: str = ""


@director.on_rest_get("/health", HealthResponse)
async def health(ctx: Context) -> HealthResponse:
    return HealthResponse(status="CogniFlow director running")


@director.on_rest_post("/message", HttpMessagePost, HttpMessageResponse)
async def message(ctx: Context, req: HttpMessagePost) -> HttpMessageResponse:
    from uuid import uuid4
    text = req.content
    session_id = str(uuid4())
    intent = classify_intent(text)
    ctx.logger.info(f"REST /message: '{text[:50]}' → intent={intent}, session={session_id[:8]}")

    state = SharedAgentState(
        chat_session_id=session_id,
        query=text,
        user_sender_address="rest-client",
        return_address=str(ctx.agent.address),
    )
    state_service.set_state(session_id, state)

    if intent == "study":
        fanout = PendingFanOut(expected_agents=[SYNC_ADDRESS], query=text, user_sender="rest-client")
        fanout.intent = "study"
        state_service.start_fanout(session_id, fanout)
        await ctx.send(INSIGHT_ADDRESS, state)
    elif intent == "focus":
        query_lower = text.lower()
        if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
            await ctx.send(RHYTHM_ADDRESS, state)
        else:
            fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS], query=text, user_sender="rest-client")
            fanout.intent = "focus"
            state_service.start_fanout(session_id, fanout)
            await ctx.send(INSIGHT_ADDRESS, state)
    elif intent == "schedule":
        await ctx.send(SYNC_ADDRESS, state)
    elif intent == "overwhelm":
        fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS, INSIGHT_ADDRESS], query=text, user_sender="rest-client")
        fanout.intent = "overwhelm"
        state_service.start_fanout(session_id, fanout)
        state_copy = SharedAgentState(chat_session_id=session_id, query=text, user_sender_address="rest-client")
        await ctx.send(RHYTHM_ADDRESS, state_copy)
        await ctx.send(INSIGHT_ADDRESS, state_copy)
    elif intent == "insight":
        state.return_address = ""
        await ctx.send(INSIGHT_ADDRESS, state)
    elif intent == "status":
        fanout = PendingFanOut(expected_agents=[RHYTHM_ADDRESS, SYNC_ADDRESS], query=text, user_sender="rest-client")
        fanout.intent = "status"
        state_service.start_fanout(session_id, fanout)
        state_copy = SharedAgentState(chat_session_id=session_id, query=text, user_sender_address="rest-client")
        await ctx.send(RHYTHM_ADDRESS, state_copy)
        await ctx.send(SYNC_ADDRESS, state_copy)
    else:
        await ctx.send(INSIGHT_ADDRESS, state)

    return HttpMessageResponse(session_id=session_id, intent=intent)


@director.on_rest_post("/result", HttpResultRequest, HttpResultResponse)
async def result(ctx: Context, req: HttpResultRequest) -> HttpResultResponse:
    if req.session_id in _completed:
        entry = _completed.pop(req.session_id)
        return HttpResultResponse(ready=True, response=entry.get("response", ""), raw_data=json.dumps(entry.get("raw_data", {})))
    return HttpResultResponse(ready=False, response="")


@director.on_message(SharedAgentState)
async def handle_agent_response(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Response from {sender[:20]}...: {state.result[:80]!r}")
    fanout = state_service.get_fanout(state.chat_session_id)

    if fanout:
        fanout.add_response(sender, state.result)
        if fanout.is_complete:
            response = generate_fanout_response(fanout)
            state_service.clear_fanout(state.chat_session_id)
            raw_data = {}
            for addr, raw in fanout.received.items():
                try:
                    parsed = json.loads(raw)
                    raw_data.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            _completed[state.chat_session_id] = {"response": response, "raw_data": raw_data}
            if fanout.user_sender != "rest-client":
                await ctx.send(fanout.user_sender, ChatMessage(
                    timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(),
                    content=[TextContent(type="text", text=response), EndSessionContent(type="end-session")],
                ))
        return

    response = generate_director_response_from_state(state)
    raw_data = {}
    try:
        raw_data = json.loads(state.result)
    except (json.JSONDecodeError, TypeError):
        pass
    _completed[state.chat_session_id] = {"response": response, "raw_data": raw_data}
    if state.user_sender_address != "rest-client":
        await ctx.send(state.user_sender_address, ChatMessage(
            timestamp=datetime.now(tz=timezone.utc), msg_id=uuid4(),
            content=[TextContent(type="text", text=response), EndSessionContent(type="end-session")],
        ))


if __name__ == "__main__":
    director.run()