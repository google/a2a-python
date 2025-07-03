import asyncio

from unittest.mock import MagicMock

import pytest

from fakeredis import FakeAsyncRedis

from a2a.server.events import EventQueue, TaskQueueExists
from a2a.server.events.redis_queue_manager import RedisQueueManager


class TestRedisQueueManager:
    @pytest.fixture
    def redis(self):
        return FakeAsyncRedis()

    @pytest.fixture
    def queue_manager(self, redis):
        return RedisQueueManager(redis)

    @pytest.fixture
    def event_queue(self):
        queue = MagicMock(spec=EventQueue)
        # Mock the tap method to return itself
        queue.tap.return_value = queue
        return queue

    @pytest.mark.asyncio
    async def test_init(self, queue_manager):
        assert queue_manager._local_queue == {}
        assert queue_manager._proxy_queue == {}
        assert isinstance(queue_manager._lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_add_new_queue(self, queue_manager, event_queue):
        """Test adding a new queue to the manager."""
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)
        assert queue_manager._local_queue[task_id] == event_queue

    @pytest.mark.asyncio
    async def test_add_existing_queue(self, queue_manager, event_queue):
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)

        with pytest.raises(TaskQueueExists):
            await queue_manager.add(task_id, event_queue)

    @pytest.mark.asyncio
    async def test_get_existing_queue(self, queue_manager, event_queue):
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)

        result = await queue_manager.get(task_id)
        assert result == event_queue

    @pytest.mark.asyncio
    async def test_get_nonexistent_queue(self, queue_manager):
        result = await queue_manager.get('nonexistent_task_id')
        assert result is None

    @pytest.mark.asyncio
    async def test_tap_existing_queue(self, queue_manager, event_queue):
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)
        event_queue.tap.assert_called_once()

        result = await queue_manager.tap(task_id)
        assert result == event_queue
        assert event_queue.tap.call_count == 2

    @pytest.mark.asyncio
    async def test_tap_nonexistent_queue(self, queue_manager):
        result = await queue_manager.tap('nonexistent_task_id')
        assert result is None

    @pytest.mark.asyncio
    async def test_close_existing_queue(self, queue_manager, event_queue):
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)

        await queue_manager.close(task_id)
        assert task_id not in queue_manager._local_queue

    @pytest.mark.asyncio
    async def test_create_or_tap_existing_queue(
        self, queue_manager, event_queue
    ):
        task_id = 'test_task_id'
        await queue_manager.add(task_id, event_queue)
        event_queue.tap.assert_called_once()

        result = await queue_manager.create_or_tap(task_id)

        assert result == event_queue
        assert event_queue.tap.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrency(self, queue_manager):
        async def add_task(task_id):
            queue = EventQueue()
            await queue_manager.add(task_id, queue)
            return task_id

        async def get_task(task_id):
            return await queue_manager.get(task_id)

        # Create 10 different task IDs
        task_ids = [f'task_{i}' for i in range(10)]

        # Add tasks concurrently
        add_tasks = [add_task(task_id) for task_id in task_ids]
        added_task_ids = await asyncio.gather(*add_tasks)

        # Verify all tasks were added
        assert set(added_task_ids) == set(task_ids)

        # Get tasks concurrently
        get_tasks = [get_task(task_id) for task_id in task_ids]
        queues = await asyncio.gather(*get_tasks)

        # Verify all queues are not None
        assert all(queue is not None for queue in queues)

        # Verify all tasks are in the manager
        for task_id in task_ids:
            assert task_id in queue_manager._local_queue
