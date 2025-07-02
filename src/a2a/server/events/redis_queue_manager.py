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
    """This implements the `QueueManager` interface using Redis for event
    queues. Primary jobs:
    1. Broadcast local events to proxy queues in other processes using redis pubsub
    2. Subscribe event messages from redis pubsub and replay to local proxy queues
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

    async def _listen_and_relay(self, task_id: str):
        c = EventConsumer(self._local_queue[task_id])
        async for event in c.consume_all():
            await self._redis.publish(
                self._task_channel_name(task_id),
                event.model_dump_json(exclude_none=True),
            )

    def _task_channel_name(self, task_id: str):
        return self._relay_channel_name + task_id

    async def _has_task_id(self, task_id: str):
        ret = await self._redis.sismember(self._task_registry_name, task_id)
        return ret

    async def _register_task_id(self, task_id: str):
        await self._redis.sadd(self._task_registry_name, task_id)
        self._background_tasks[task_id] = asyncio.create_task(
            self._listen_and_relay(task_id)
        )

    async def _remove_task_id(self, task_id: str):
        if task_id in self._background_tasks:
            self._background_tasks[task_id].cancel(
                'task_id is closed: ' + task_id
            )
        return await self._redis.srem(self._task_registry_name, task_id)

    async def _subscribe_remote_task_events(self, task_id: str):
        await self._pubsub.subscribe(
            **{
                self._task_channel_name(task_id): partial(
                    self._relay_remote_events, task_id
                )
            }
        )

    def _unsubscribe_remote_task_events(self, task_id: str):
        self._pubsub.unsubscribe(self._task_channel_name(task_id))

    def _relay_remote_events(self, task_id: str, event_json: str):
        if task_id in self._proxy_queue:
            event = Event.model_validate_json(event_json)
            self._proxy_queue[task_id].enqueue_event(event)

    async def add(self, task_id: str, queue: EventQueue) -> None:
        async with self._lock:
            if await self._has_task_id(task_id):
                raise TaskQueueExists()
            self._local_queue[task_id] = queue
            await self._register_task_id(task_id)

    async def get(self, task_id: str) -> EventQueue | None:
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
        event_queue = await self.get(task_id)
        if event_queue:
            return event_queue.tap()
        return None

    async def close(self, task_id: str) -> None:
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
