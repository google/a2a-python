import asyncio
import logging
import uuid

from asyncio import Task
from typing import Any

from pydantic import TypeAdapter
from redis.asyncio import Redis

from a2a.server.events import (
    Event,
    EventConsumer,
    EventQueue,
    NoTaskQueue,
    QueueManager,
    TaskQueueExists,
)


logger = logging.getLogger(__name__)


class RedisQueueManager(QueueManager):
    """This implements the `QueueManager` interface using Redis for event.

    It will broadcast local events to proxy queues in other processes using redis pubsub, and subscribe event messages from redis pubsub and replay to local proxy queues.

    Args:
        redis_client(Redis): asyncio redis connection.
        relay_channel_key_prefix(str): prefix for pubsub channel key generation.
        task_registry_key(str): key for set data where stores active `task_id`s.
        task_id_ttl_in_second: TTL for task id in global registry
        node_id: A unique id to be associated with task id in global registry. If node id is not matched, events won't be populated to queues in other `RedisQueueManager`s.
    """

    def __init__(
        self,
        redis_client: Redis,
        relay_channel_key_prefix: str = 'a2a.event.relay.',
        task_registry_key: str = 'a2a.event.registry',
        task_id_ttl_in_second: int = 60 * 60 * 24,
        node_id: str = str(uuid.uuid4()),
    ):
        self._redis = redis_client
        self._local_queue: dict[str, EventQueue] = {}
        self._proxy_queue: dict[str, EventQueue] = {}
        self._lock = asyncio.Lock()
        self._pubsub = redis_client.pubsub()
        self._relay_channel_name = relay_channel_key_prefix
        self._background_tasks: dict[str, Task] = {}
        self._task_registry_name = task_registry_key
        self._pubsub_listener_task: Task | None = None
        self._task_id_ttl_in_second = task_id_ttl_in_second
        self._node_id = node_id

    def _task_channel_name(self, task_id: str) -> str:
        return self._relay_channel_name + task_id

    async def _has_task_id(self, task_id: str) -> bool:
        ret = await self._redis.hget(self._task_registry_name, task_id)
        return ret is not None

    async def _register_task_id(self, task_id: str) -> None:
        await self._redis.hsetex(
            name=self._task_registry_name,
            key=task_id,
            value=self._node_id,
            ex=self._task_id_ttl_in_second,
        )
        logger.debug(
            f'Registered task_id {task_id} to node {self._node_id} in registry.'
        )
        task_started_event = asyncio.Event()

        async def _wrapped_listen_and_relay() -> None:
            task_started_event.set()
            c = EventConsumer(self._local_queue[task_id].tap())
            async for event in c.consume_all():
                logger.debug(
                    f'Publishing event for task {task_id} in QM {self}: {event}'
                )
                expected_node_id = await self._redis.hget(
                    self._task_registry_name, task_id
                )
                expected_node_id = (
                    expected_node_id.decode('utf-8')
                    if hasattr(expected_node_id, 'decode')
                    else expected_node_id
                )
                if expected_node_id == self._node_id:
                    # publish message
                    await self._redis.publish(
                        self._task_channel_name(task_id),
                        event.model_dump_json(exclude_none=True),
                    )
                    # update TTL for task_id
                    await self._redis.hsetex(
                        name=self._task_registry_name,
                        key=task_id,
                        value=self._node_id,
                        ex=self._task_id_ttl_in_second,
                    )
                else:
                    logger.error(
                        f'Task {task_id} is not registered on this node. Expected node id: {expected_node_id}'
                    )
                    break

        self._background_tasks[task_id] = asyncio.create_task(
            _wrapped_listen_and_relay()
        )
        await task_started_event.wait()
        logger.debug(f'Started to listen and relay events for task {task_id}')

    async def _remove_task_id(self, task_id: str) -> bool:
        if task_id in self._background_tasks:
            self._background_tasks[task_id].cancel(
                'task_id is closed: ' + task_id
            )
        return await self._redis.hdel(self._task_registry_name, task_id) == 1

    async def _subscribe_remote_task_events(self, task_id: str) -> None:
        channel_id = self._task_channel_name(task_id)
        await self._pubsub.subscribe(**{channel_id: self._relay_remote_events})
        # this is a global listener to handle incoming pubsub events
        if not self._pubsub_listener_task:
            logger.debug('Creating pubsub listener task.')
            self._pubsub_listener_task = asyncio.create_task(
                self._consume_pubsub_messages()
            )
        logger.debug(f'Subscribed for remote events for task {task_id}')

    async def _consume_pubsub_messages(self) -> None:
        async for _ in self._pubsub.listen():
            pass

    async def _relay_remote_events(
        self, subscription_event: dict[str, Any]
    ) -> None:
        if (
            'channel' not in subscription_event
            or 'data' not in subscription_event
        ):
            logger.warning(
                f'channel or data is absent in subscription event: {subscription_event}'
            )
            return

        channel_id: str = subscription_event['channel'].decode('utf-8')
        data_string: str = subscription_event['data'].decode('utf-8')
        task_id = channel_id.split('.')[-1]
        if task_id not in self._proxy_queue:
            logger.warning(f'task_id {task_id} not found in proxy queue')
            return

        try:
            logger.debug(
                f'Received event for task_id {task_id} in QM {self}: {data_string}'
            )
            event: Event = TypeAdapter(Event).validate_json(data_string)
        except Exception as e:
            logger.warning(
                f'Failed to parse event from subscription event: {subscription_event}: {e}'
            )
            return

        logger.debug(
            f'Enqueuing event for task_id {task_id} in QM {self}: {event}'
        )
        await self._proxy_queue[task_id].enqueue_event(event)

    async def _unsubscribe_remote_task_events(self, task_id: str) -> None:
        # unsubscribe channel for given task_id
        await self._pubsub.unsubscribe(self._task_channel_name(task_id))
        # release global listener if not channel is subscribed
        if not self._pubsub.subscribed and self._pubsub_listener_task:
            self._pubsub_listener_task.cancel()
            self._pubsub_listener_task = None

    async def add(self, task_id: str, queue: EventQueue) -> None:
        """Add a new local event queue for the specified task.

        Args:
            task_id (str): The identifier of the task.
            queue (EventQueue): The event queue to be added.

        Raises:
            TaskQueueExists: If a queue for the task already exists.
        """
        logger.debug(f'add {task_id}')
        async with self._lock:
            if await self._has_task_id(task_id):
                raise TaskQueueExists()
            self._local_queue[task_id] = queue
            await self._register_task_id(task_id)
            logger.debug(f'Local queue is created for task {task_id}')

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
        logger.debug(f'get {task_id}')
        async with self._lock:
            # lookup locally
            if task_id in self._local_queue:
                logger.debug(f'Got local queue for task_id {task_id}')
                return self._local_queue[task_id]
            # lookup globally
            if await self._has_task_id(task_id):
                if task_id not in self._proxy_queue:
                    logger.debug(f'Creating proxy queue for {task_id}')
                    queue = EventQueue()
                    self._proxy_queue[task_id] = queue
                    await self._subscribe_remote_task_events(task_id)
                logger.debug(f'Got proxy queue for task_id {task_id}')
                return self._proxy_queue[task_id]
            logger.warning(
                f'Attempted to get non-existing queue for task {task_id}'
            )
            return None

    async def tap(self, task_id: str) -> EventQueue | None:
        """Create a duplicate reference to an existing event queue for the task.

        Args:
            task_id (str): The identifier of the task.

        Returns:
            EventQueue | None: A new reference to the event queue if it exists, otherwise None.
        """
        logger.debug(f'tap {task_id}')
        event_queue = await self.get(task_id)
        if event_queue:
            logger.debug(f'Tapping event queue for task: {task_id}')
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
        logger.debug(f'close {task_id}')
        async with self._lock:
            if task_id in self._local_queue:
                # remove from global registry if a local queue is closed
                await self._remove_task_id(task_id)
                # close locally
                queue = self._local_queue.pop(task_id)
                await queue.close()
                logger.debug(f'Closing local queue for task {task_id}')
                return

            if task_id in self._proxy_queue:
                # close proxy queue
                queue = self._proxy_queue.pop(task_id)
                await queue.close()
                # unsubscribe from remote, but don't remove from global registry
                await self._unsubscribe_remote_task_events(task_id)
                logger.debug(f'Closing proxy queue for task {task_id}')
                return

            logger.warning(
                f'Attempted to close non-existing queue found for task {task_id}'
            )
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
        logger.debug(f'create_or_tap {task_id}')
        async with self._lock:
            if await self._has_task_id(task_id):
                # if it's a local queue, tap directly
                if task_id in self._local_queue:
                    logger.debug(f'Tapping a local queue for task {task_id}')
                    return self._local_queue[task_id].tap()

                # if it's a proxy queue, tap the proxy
                if task_id not in self._proxy_queue:
                    # if the proxy is not created, create the proxy
                    queue = EventQueue()
                    self._proxy_queue[task_id] = queue
                    await self._subscribe_remote_task_events(task_id)
                logger.debug(f'Tapping a proxy queue for task {task_id}')
                return self._proxy_queue[task_id].tap()
            # the task doesn't exist before, create a local queue
            queue = EventQueue()
            self._local_queue[task_id] = queue
            await self._register_task_id(task_id)
            logger.debug(f'Creating a local queue for task {task_id}')
            return queue
