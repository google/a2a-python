from abc import ABC, abstractmethod

from a2a.types import Task


class PushNotificationSender(ABC):
    """Interface for sending push notifications for tasks."""

    @abstractmethod
    async def send_notification(self, task: Task) -> None:
        """Sends a push notification containing the latest task state."""
