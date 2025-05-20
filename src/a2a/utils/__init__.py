"""Utility functions for the A2A Python SDK."""

from a2a.utils.artifact import (
    new_artifact,
    new_data_artifact,
    new_text_artifact,
)
from a2a.utils.helpers import (
    append_artifact_to_task,
    are_modalities_compatible,
    build_text_artifact,
    create_task_obj,
)
from a2a.utils.message import (
    get_message_text,
    get_text_parts,
    new_agent_parts_message,
    new_agent_text_message,
)
from a2a.utils.task import (
    completed_task,
    new_task,
)


__all__ = [
    'append_artifact_to_task',
    'are_modalities_compatible',
    'build_text_artifact',
    'completed_task',
    'create_task_obj',
    'get_message_text',
    'get_text_parts',
    'new_agent_parts_message',
    'new_agent_text_message',
    'new_artifact',
    'new_data_artifact',
    'new_task',
    'new_text_artifact',
]
