from a2a.types import AgentCard, AgentExtension


HTTP_EXTENSION_HEADER = 'X-A2A-Extensions'


def find_extension_by_uri(card: AgentCard, uri: str) -> AgentExtension | None:
    """Find an AgentExtension in an AgentCard given a uri."""
    for ext in card.capabilities.extensions or []:
        if ext.uri == uri:
            return ext

    return None
