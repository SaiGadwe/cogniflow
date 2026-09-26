from uagents import Model


class SharedAgentState(Model):
    """
    Shared communication contract between CogniFlow agents.

    Supports hub-and-spoke (director <-> agent) and chained
    communication (agent -> agent -> director) via return_address
    and chain_data fields.
    """

    chat_session_id: str
    query: str
    user_sender_address: str
    result: str = ""
    return_address: str = ""
    chain_data: str = ""