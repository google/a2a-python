from abc import ABC, abstractmethod

from a2a.types import PushNotificationConfig, Task


class PushNotifier(ABC):
    """PushNotifier interface to store, retrieve push notification for tasks and send push notifications."""

    @abstractmethod
    async def set_info(
        self, task_id: str, notification_config: PushNotificationConfig
    ):
        pass

    @abstractmethod
    async def get_info(self, task_id: str) -> PushNotificationConfig | None:
        pass

    @abstractmethod
    async def delete_info(self, task_id: str):
        pass

    @abstractmethod
    async def send_notification(self, task: Task):
        pass
