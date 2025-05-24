import json
import logging

import asyncpg

from a2a.server.tasks.task_store import TaskStore
from a2a.types import Task


logger = logging.getLogger(__name__)


class PostgreSQLTaskStore(TaskStore):
    """PostgreSQL implementation of TaskStore.

    Stores task objects in a PostgreSQL database.
    """

    def __init__(
        self,
        url: str,
        table_name: str = 'tasks',
        create_table: bool = True,
    ) -> None:
        """Initializes the PostgreSQLTaskStore.

        Args:
            url: PostgreSQL connection string in the format:
                postgresql://username:password@hostname:port/database
            table_name: The name of the table to store tasks in
            create_table: Whether to create the table if it doesn't exist
        """
        logger.debug('Initializing PostgreSQLTaskStore')
        self.url = url
        self.table_name = table_name
        self.create_table = create_table

        self.pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Initialize the database connection pool and create the table
        if needed.
        """
        if self.pool is not None:
            return

        logger.debug('Creating connection pool')
        self.pool = await asyncpg.create_pool(self.url)

        if self.create_table:
            async with self.pool.acquire() as conn:
                logger.debug('Creating tasks table if not exists')
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        data JSONB NOT NULL

                    )
                    """
                )

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def save(self, task: Task) -> None:
        """Saves or updates a task in the PostgreSQL store."""
        await self._ensure_initialized()

        assert self.pool is not None
        async with self.pool.acquire() as conn, conn.transaction():
            task_json = task.model_dump()

            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, data)
                VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE
                SET data = $2
                """,
                task.id,
                json.dumps(task_json),
            )

            logger.info('Task %s saved successfully.', task.id)

    async def get(self, task_id: str) -> Task | None:
        """Retrieves a task from the PostgreSQL store by ID."""
        await self._ensure_initialized()

        assert self.pool is not None
        async with self.pool.acquire() as conn, conn.transaction():
            logger.debug('Attempting to get task with id: %s', task_id)

            row = await conn.fetchrow(
                f'SELECT data FROM {self.table_name} WHERE id = $1',
                task_id,
            )

            if row:
                task_json = json.loads(row['data'])
                task = Task.model_validate(task_json)
                logger.debug('Task %s retrieved successfully.', task_id)
                return task

            logger.debug('Task %s not found in store.', task_id)
            return None

    async def delete(self, task_id: str) -> None:
        """Deletes a task from the PostgreSQL store by ID."""
        await self._ensure_initialized()

        assert self.pool is not None
        async with self.pool.acquire() as conn, conn.transaction():
            logger.debug('Attempting to delete task with id: %s', task_id)

            result = await conn.execute(
                f'DELETE FROM {self.table_name} WHERE id = $1',
                task_id,
            )

            if result.split()[-1] != '0':  # Check if rows were affected
                logger.info('Task %s deleted successfully.', task_id)
            else:
                logger.warning(
                    'Attempted to delete nonexistent task with id: %s',
                    task_id,
                )

    async def _ensure_initialized(self) -> None:
        """Ensure the database connection is initialized."""
        if self.pool is None:
            await self.initialize()
