import asyncio

from asyncio import Task
from functools import partial

from redis.asyncio import Redis

from a2a.server.events import (
    Event,
    EventConsumer,
    EventQueue,
    NoTaskQueue,
    QueueManager,
    TaskQueueExists,
)


class RedisQueueManager(QueueManager):
    """This implements the `QueueManager` interface using Redis for event.

    It will broadcast local events to proxy queues in other processes using redis pubsub, and subscribe event messages from redis pubsub and replay to local proxy queues.

    Args:
        redis_client(Redis): asyncio redis connection.
        relay_channel_key_prefix(str): prefix for pubsub channel key generation.
        task_registry_key(str): key for set data where stores active `task_id`s.
    """

    def __init__(
        self,
        redis_client: Redis,
        relay_channel_key_prefix: str = 'a2a.event.relay.',
        task_registry_key: str = 'a2a.event.registry',
    ):
        self._redis = redis_client
        self._local_queue: dict[str, EventQueue] = {}
        self._proxy_queue: dict[str, EventQueue] = {}
        self._lock = asyncio.Lock()
        self._pubsub = redis_client.pubsub()
        self._relay_channel_name = relay_channel_key_prefix
        self._background_tasks: dict[str, Task] = {}
        self._task_registry_name = task_registry_key

    async def _listen_and_relay(self, task_id: str) -> None:
        c = EventConsumer(self._local_queue[task_id])
        async for event in c.consume_all():
            await self._redis.publish(
                self._task_channel_name(task_id),
                event.model_dump_json(exclude_none=True),
            )

    def _task_channel_name(self, task_id: str) -> str:
        return self._relay_channel_name + task_id

    async def _has_task_id(self, task_id: str) -> bool:
        ret = await self._redis.sismember(self._task_registry_name, task_id)
        return ret == 1

    async def _register_task_id(self, task_id: str) -> None:
        await self._redis.sadd(self._task_registry_name, task_id)
        self._background_tasks[task_id] = asyncio.create_task(
            self._listen_and_relay(task_id)
        )

    async def _remove_task_id(self, task_id: str) -> bool:
        if task_id in self._background_tasks:
            self._background_tasks[task_id].cancel(
                'task_id is closed: ' + task_id
            )
        return await self._redis.srem(self._task_registry_name, task_id) == 1

    async def _subscribe_remote_task_events(self, task_id: str) -> None:
        await self._pubsub.subscribe(
            **{
                self._task_channel_name(task_id): partial(
                    self._relay_remote_events, task_id
                )
            }
        )

    def _unsubscribe_remote_task_events(self, task_id: str) -> None:
        self._pubsub.unsubscribe(self._task_channel_name(task_id))

    def _relay_remote_events(self, task_id: str, event_json: str) -> None:
        if task_id in self._proxy_queue:
            event = Event.model_validate_json(event_json)
            self._proxy_queue[task_id].enqueue_event(event)

    async def add(self, task_id: str, queue: EventQueue) -> None:
        """Add a new local event queue for the specified task.

        Args:
            task_id (str): The identifier of the task.
            queue (EventQueue): The event queue to be added.

        Raises:
            TaskQueueExists: If a queue for the task already exists.
        """
        async with self._lock:
            if await self._has_task_id(task_id):
                raise TaskQueueExists()
            self._local_queue[task_id] = queue
            await self._register_task_id(task_id)

    async def get(self, task_id: str) -> EventQueue | None:
        """Get the event queue associated with the given task ID.

        This method first checks if there is a local queue for the task.
        If not found, it checks the global registry and creates a proxy queue
        if the task exists globally but not locally.

        Args:
            task_id (str): The identifier of the task.

        Returns:
            EventQueue | None: The event queue if found, otherwise None.
        """
        async with self._lock:
            # lookup locally
            if task_id in self._local_queue:
                return self._local_queue[task_id]
            # lookup globally
            if await self._has_task_id(task_id):
                if task_id not in self._proxy_queue:
                    queue = EventQueue()
                    self._proxy_queue[task_id] = queue
                    await self._subscribe_remote_task_events(task_id)
                return self._proxy_queue[task_id]
            return None

    async def tap(self, task_id: str) -> EventQueue | None:
        """Create a duplicate reference to an existing event queue for the task.

        Args:
            task_id (str): The identifier of the task.

        Returns:
            EventQueue | None: A new reference to the event queue if it exists, otherwise None.
        """
        event_queue = await self.get(task_id)
        if event_queue:
            return event_queue.tap()
        return None

    async def close(self, task_id: str) -> None:
        """Close the event queue associated with the given task ID.

        If the queue is a local queue, it will be removed from both the local store
        and the global registry. If it's a proxy queue, only the proxy will be closed
        and unsubscribed from remote events without removing from the global registry.

        Args:
            task_id (str): The identifier of the task.

        Raises:
            NoTaskQueue: If no queue exists for the given task ID.
        """
        async with self._lock:
            if task_id in self._local_queue:
                # close locally
                queue = self._local_queue.pop(task_id)
                await queue.close()
                # remove from global registry if a local queue is closed
                await self._remove_task_id(task_id)
                return

            if task_id in self._proxy_queue:
                # close proxy queue
                queue = self._proxy_queue.pop(task_id)
                await queue.close()
                # unsubscribe from remote, but don't remove from global registry
                self._unsubscribe_remote_task_events(task_id)
                return

            raise NoTaskQueue()

    async def create_or_tap(self, task_id: str) -> EventQueue:
        """Create a new local queue or return a reference to an existing one.

        If the task already has a queue (either local or proxy), this method returns
        a reference to that queue. Otherwise, a new local queue is created and registered.

        Args:
            task_id (str): The identifier of the task.

        Returns:
            EventQueue: An event queue associated with the given task ID.
        """
        async with self._lock:
            if await self._has_task_id(task_id):
                # if it's a local queue, tap directly
                if task_id in self._local_queue:
                    return self._local_queue[task_id].tap()

                # if it's a proxy queue, tap the proxy
                if task_id in self._proxy_queue:
                    return self._proxy_queue[task_id].tap()

                # if the proxy is not created, create the proxy and return
                queue = EventQueue()
                self._proxy_queue[task_id] = queue
                await self._subscribe_remote_task_events(task_id)
                return self._proxy_queue[task_id]
            # the task doesn't exist before, create a local queue
            queue = EventQueue()
            self._local_queue[task_id] = queue
            await self._register_task_id(task_id)
            return queue
