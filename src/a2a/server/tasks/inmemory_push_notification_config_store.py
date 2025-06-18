import asyncio
import logging

from a2a.server.tasks.push_notification_config_store import PushNotificationConfigStore
from a2a.types import PushNotificationConfig

logger = logging.getLogger(__name__)


class InMemoryPushNotificationConfigStore(PushNotificationConfigStore):
    """In-memory implementation of PushNotificationConfigStore interface.

    Stores push notification configurations in memory and uses an httpx client
    to send notifications.
    """
    def __init__(self) -> None:
        """Initializes the InMemoryPushNotifier.

        Args:
            httpx_client: An async HTTP client instance to send notifications.
        """
        self.lock = asyncio.Lock()
        self._push_notification_infos: dict[str, PushNotificationConfig] = {}

    async def set_info(
        self, task_id: str, notification_config: PushNotificationConfig
    ):
        """Sets or updates the push notification configuration for a task in memory."""
        async with self.lock:
            self._push_notification_infos[task_id] = notification_config

    async def get_info(self, task_id: str) -> PushNotificationConfig | None:
        """Retrieves the push notification configuration for a task from memory."""
        async with self.lock:
            return self._push_notification_infos.get(task_id)



    async def delete_info(self, task_id: str):
        """Deletes the push notification configuration for a task from memory."""
        async with self.lock:
            if task_id in self._push_notification_infos:
                del self._push_notification_infos[task_id]
