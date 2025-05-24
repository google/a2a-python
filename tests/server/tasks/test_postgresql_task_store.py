import json
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from a2a.server.tasks.postgresql_task_store import PostgreSQLTaskStore
from a2a.types import Task, TaskState, TaskStatus

# Use a proper Task object instead of a dict for the minimal task
task_status = TaskStatus(state=TaskState.submitted)
MINIMAL_TASK_OBJ = Task(
    id='task-abc',
    contextId='session-xyz',
    status=task_status,
    kind='task',
)


# Get PostgreSQL connection string from environment or use a default for testing
POSTGRES_TEST_DSN = os.environ.get(
    'POSTGRES_TEST_DSN',
    'postgresql://postgres:postgres@localhost:5432/a2a_test',
)


@pytest_asyncio.fixture
async def postgres_store() -> AsyncGenerator[PostgreSQLTaskStore, None]:
    """Fixture that provides a PostgreSQLTaskStore connected to a real database.

    This fixture requires a running PostgreSQL instance
    """

    store = PostgreSQLTaskStore(POSTGRES_TEST_DSN)
    await store.initialize()

    # Clean up any test data that might be left from previous runs
    if store.pool is not None:
        async with store.pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {store.table_name} WHERE id LIKE 'test-%'"
            )

    yield store
    await store.close()


@pytest.mark.asyncio
async def test_initialize_creates_table(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test that initialize creates the table if it doesn't exist."""
    await postgres_store.initialize()

    # Verify the pool was created
    assert postgres_store.pool is not None

    # Verify the table creation query was executed
    async with postgres_store.pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval(
                f"SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{postgres_store.table_name}')"
            )
            assert exists


@pytest.mark.asyncio
async def test_save_task(postgres_store: PostgreSQLTaskStore) -> None:
    """Test saving a task to the PostgreSQL store."""
    # Use the pre-created Task object to avoid serialization issues
    task = MINIMAL_TASK_OBJ
    await postgres_store.save(task)
    assert postgres_store.pool is not None

    # Verify the insert query was executed
    async with postgres_store.pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                f'SELECT data FROM {postgres_store.table_name} WHERE id = $1',
                task.id,
            )
            assert row is not None
            # Convert the task to a dictionary with proper enum handling

            # Parse the JSON string from the database
            db_dict = (
                json.loads(row['data'])
                if isinstance(row['data'], str)
                else row['data']
            )
            assert db_dict == task.model_dump()


@pytest.mark.asyncio
async def test_get_task(postgres_store: PostgreSQLTaskStore) -> None:
    """Test retrieving a task from the PostgreSQL store."""
    retrieved_task = await postgres_store.get(MINIMAL_TASK_OBJ.id)

    # Verify the task was correctly reconstructed
    assert retrieved_task is not None
    assert retrieved_task.id == MINIMAL_TASK_OBJ.id
    assert retrieved_task.contextId == MINIMAL_TASK_OBJ.contextId


@pytest.mark.asyncio
async def test_get_nonexistent_task(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test retrieving a nonexistent task."""

    retrieved_task = await postgres_store.get('nonexistent')

    # Verify None was returned
    assert retrieved_task is None


@pytest.mark.asyncio
async def test_delete_task(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test deleting a task from the PostgreSQL store."""
    await postgres_store.initialize()
    await postgres_store.delete(MINIMAL_TASK_OBJ.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_task(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test deleting a nonexistent task."""
    await postgres_store.initialize()
    await postgres_store.delete('nonexistent')


@pytest.mark.asyncio
async def test_close_connection_pool(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test closing the database connection pool."""
    await postgres_store.close()
    assert postgres_store.pool is None


@pytest.mark.asyncio
async def test_save_and_get_task(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test for saving and retrieving a task from a real PostgreSQL database."""
    # Create a unique test task
    test_task = Task(
        id='test-1',
        contextId='test-session-1',
        status=TaskStatus(state=TaskState.submitted),
        kind='task',
    )

    # Save the task
    await postgres_store.save(test_task)

    # Retrieve the task
    retrieved_task = await postgres_store.get(test_task.id)

    # Verify task was retrieved correctly
    assert retrieved_task is not None
    assert retrieved_task.id == test_task.id
    assert retrieved_task.contextId == test_task.contextId
    assert retrieved_task.status.state == test_task.status.state

    # Clean up
    await postgres_store.delete(test_task.id)

    # Verify deletion
    deleted_task = await postgres_store.get(test_task.id)
    assert deleted_task is None


@pytest.mark.asyncio
async def test_update_task(
    postgres_store: PostgreSQLTaskStore,
) -> None:
    """Test for updating a task in a real PostgreSQL database."""
    # Create a test task
    test_task = Task(
        id='test-2',
        contextId='test-session-2',
        status=TaskStatus(state=TaskState.submitted),
        kind='task',
    )

    # Save the task
    await postgres_store.save(test_task)

    # Update the task
    updated_task = test_task.model_copy(deep=True)
    updated_task.status.state = TaskState.completed
    await postgres_store.save(updated_task)

    # Retrieve the updated task
    retrieved_task = await postgres_store.get(test_task.id)

    # Verify the update was successful
    assert retrieved_task is not None
    assert retrieved_task.status.state == TaskState.completed

    # Clean up
    await postgres_store.delete(test_task.id)
