import logging

import httpx

from a2a.server.tasks.push_notification_config_store import (
    PushNotificationConfigStore,
)
from a2a.server.tasks.push_notification_sender import PushNotificationSender
from a2a.types import Task, PushNotificationConfig


logger = logging.getLogger(__name__)


class BasePushNotificationSender(PushNotificationSender):
    """Base implementation of PushNotificationSender interface."""

    def __init__(self, httpx_client: httpx.AsyncClient, config_store: PushNotificationConfigStore) -> None:
        """Initializes the BasePushNotificationSender.

        Args:
            httpx_client: An async HTTP client instance to send notifications.
            config_store: A PushNotificationConfigStore instance to retrieve configurations.
        """
        self._client = httpx_client
        self._config_store = config_store

    async def send_notification(self, task: Task) -> None:
        """Sends a push notification for a task if configuration exists."""
        push_configs = await self._config_store.get_info(task.id)
        if not push_configs:
            return
        
        for push_info in push_configs:
            await self._dispatch_notification(task, push_info)

    async def _dispatch_notification(self, task: Task, push_info: PushNotificationConfig) -> None:
        url = push_info.url
        try:
            response = await self._client.post(
                url, json=task.model_dump(mode='json', exclude_none=True)
            )
            response.raise_for_status()
            logger.info(f'Push-notification sent for URL: {url}')
        except Exception as e:
            logger.error(f'Error sending push-notification: {e}')
