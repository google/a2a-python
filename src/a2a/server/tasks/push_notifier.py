from abc import ABC, abstractmethod

from a2a.types import PushNotificationConfig, Task


class PushNotifier(ABC):
    """PushNotifier interface to store, retrieve push notification for tasks and send push notifications."""

    @abstractmethod
    async def set_info(
        self, task_id: str, notification_config: PushNotificationConfig
    ):
        """Sets or updates the push notification configuration for a task."""

    @abstractmethod
    async def get_info(self, task_id: str) -> PushNotificationConfig | None:
        """Retrieves the push notification configuration for a task."""

    @abstractmethod
    async def delete_info(self, task_id: str):
        """Deletes the push notification configuration for a task."""

    @abstractmethod
    async def send_notification(self, task: Task):
        """Sends a push notification containing the latest task state."""
