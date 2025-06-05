import asyncio
import logging

import httpx

from a2a.server.tasks.push_notifier import PushNotifier
from a2a.types import PushNotificationConfig, Task


logger = logging.getLogger(__name__)


class InMemoryPushNotifier(PushNotifier):
    """In-memory implementation of PushNotifier interface.

    Stores push notification configurations in memory and uses an httpx client
    to send notifications.
    """

    def __init__(self, httpx_client: httpx.AsyncClient) -> None:
        """Initializes the InMemoryPushNotifier.

        Args:
            httpx_client: An async HTTP client instance to send notifications.
        """
        self._client = httpx_client
        self.lock = asyncio.Lock()
        self._push_notification_infos: dict[str, PushNotificationConfig] = {}

    async def set_info(
        self, task_id: str, notification_config: PushNotificationConfig
    ) -> None:
        """Sets or updates the push notification configuration for a task in memory."""
        async with self.lock:
            self._push_notification_infos[task_id] = notification_config

    async def get_info(self, task_id: str) -> PushNotificationConfig | None:
        """Retrieves the push notification configuration for a task from memory."""
        async with self.lock:
            return self._push_notification_infos.get(task_id)

    async def delete_info(self, task_id: str) -> None:
        """Deletes the push notification configuration for a task from memory."""
        async with self.lock:
            if task_id in self._push_notification_infos:
                del self._push_notification_infos[task_id]

    async def send_notification(self, task: Task) -> None:
        """Sends a push notification for a task if configuration exists."""
        push_info = await self.get_info(task.id)
        if not push_info:
            return
        url = push_info.url

        try:
            response = await self._client.post(
                url, json=task.model_dump(mode='json', exclude_none=True)
            )
            response.raise_for_status()
            logger.info(f'Push-notification sent for URL: {url}')
        except Exception as e:
            logger.error(f'Error sending push-notification: {e}')
