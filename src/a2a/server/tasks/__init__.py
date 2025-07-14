"""Components for managing tasks within the A2A server."""

import logging

from a2a.server.tasks.base_push_notification_sender import (
    BasePushNotificationSender,
)
from a2a.server.tasks.inmemory_push_notification_config_store import (
    InMemoryPushNotificationConfigStore,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.push_notification_config_store import (
    PushNotificationConfigStore,
)
from a2a.server.tasks.push_notification_sender import PushNotificationSender
from a2a.server.tasks.result_aggregator import ResultAggregator
from a2a.server.tasks.task_manager import TaskManager
from a2a.server.tasks.task_store import TaskStore
from a2a.server.tasks.task_updater import TaskUpdater


log = logging.getLogger(__name__)

try:
    from a2a.server.tasks.database_task_store import DatabaseTaskStore
except ImportError as e:
    # If the database task store is not available, we can still use in-memory stores.
    log.debug(
        'DatabaseTaskStore not loaded. This is expected if database dependencies are not installed. Error: %s',
        e,
    )
    DatabaseTaskStore = None

__all__ = [
    'BasePushNotificationSender',
    'DatabaseTaskStore',
    'InMemoryPushNotificationConfigStore',
    'InMemoryTaskStore',
    'PushNotificationConfigStore',
    'PushNotificationSender',
    'ResultAggregator',
    'TaskManager',
    'TaskStore',
    'TaskUpdater',
]
