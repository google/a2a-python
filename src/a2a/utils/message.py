"""Utility functions for creating and handling A2A Message objects."""

import uuid

from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
)


def new_agent_text_message(
    text: str,
    context_id: str | None = None,
    task_id: str | None = None,
) -> Message:
    """Creates a new agent message containing a single TextPart.

    Args:
        text: The text content of the message.
        context_id: The context ID for the message.
        task_id: The task ID for the message.

    Returns:
        A new `Message` object with role 'agent'.
    """
    return Message(
        role=Role.agent,
        parts=[Part(root=TextPart(text=text))],
        messageId=str(uuid.uuid4()),
        taskId=task_id,
        contextId=context_id,
    )


def new_agent_parts_message(
    parts: list[Part],
    context_id: str | None = None,
    task_id: str | None = None,
) -> Message:
    """Creates a new agent message containing a list of Parts.

    Args:
        parts: The list of `Part` objects for the message content.
        context_id: The context ID for the message.
        task_id: The task ID for the message.

    Returns:
        A new `Message` object with role 'agent'.
    """
    return Message(
        role=Role.agent,
        parts=parts,
        messageId=str(uuid.uuid4()),
        taskId=task_id,
        contextId=context_id,
    )


def get_text_parts(parts: list[Part]) -> list[str]:
    """Extracts text content from all TextPart objects in a list of Parts.

    Args:
        parts: A list of `Part` objects.

    Returns:
        A list of strings containing the text content from any `TextPart` objects found.
    """
    return [part.root.text for part in parts if isinstance(part.root, TextPart)]


def get_message_text(message: Message, delimiter: str = '\n') -> str:
    """Extracts and joins all text content from a Message's parts.

    Args:
        message: The `Message` object.
        delimiter: The string to use when joining text from multiple TextParts.

    Returns:
        A single string containing all text content, or an empty string if no text parts are found.
    """
    return delimiter.join(get_text_parts(message.parts))
