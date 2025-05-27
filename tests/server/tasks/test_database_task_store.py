import os

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from _pytest.mark.structures import ParameterSet


# Skip entire test module if SQLAlchemy is not installed
pytest.importorskip('sqlalchemy', reason='Database tests require SQLAlchemy')

# Now safe to import SQLAlchemy-dependent modules
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.inspection import inspect

from a2a.server.models import Base, TaskModel  # Important: To get Base.metadata
from a2a.server.tasks.database_task_store import DatabaseTaskStore
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)


# DSNs for different databases
SQLITE_TEST_DSN = 'sqlite+aiosqlite:///file::memory:?cache=shared'
# SQLITE_TEST_DSN_FILE = "sqlite+aiosqlite:///./test_param.db" # For file-based SQLite inspection
POSTGRES_TEST_DSN = os.environ.get(
    'POSTGRES_TEST_DSN'
)  # e.g., "postgresql+asyncpg://user:pass@host:port/dbname"
MYSQL_TEST_DSN = os.environ.get(
    'MYSQL_TEST_DSN'
)  # e.g., "mysql+aiomysql://user:pass@host:port/dbname"

# Parameterization for the db_store fixture
DB_CONFIGS: list[ParameterSet | tuple[str | None, str]] = [
    pytest.param((SQLITE_TEST_DSN, 'sqlite'), id='sqlite')
]

if POSTGRES_TEST_DSN:
    DB_CONFIGS.append(
        pytest.param((POSTGRES_TEST_DSN, 'postgresql'), id='postgresql')
    )
else:
    DB_CONFIGS.append(
        pytest.param(
            (None, 'postgresql'),
            marks=pytest.mark.skip(reason='POSTGRES_TEST_DSN not set'),
            id='postgresql_skipped',
        )
    )

if MYSQL_TEST_DSN:
    DB_CONFIGS.append(pytest.param((MYSQL_TEST_DSN, 'mysql'), id='mysql'))
else:
    DB_CONFIGS.append(
        pytest.param(
            (None, 'mysql'),
            marks=pytest.mark.skip(reason='MYSQL_TEST_DSN not set'),
            id='mysql_skipped',
        )
    )


# Minimal Task object for testing - remains the same
task_status_submitted = TaskStatus(
    state=TaskState.submitted, timestamp='2023-01-01T00:00:00Z'
)
MINIMAL_TASK_OBJ = Task(
    id='task-abc',
    contextId='session-xyz',
    status=task_status_submitted,
    kind='task',
    metadata={'test_key': 'test_value'},
    artifacts=[],
    history=[],
)


@pytest_asyncio.fixture(params=DB_CONFIGS)
async def db_store_parameterized(
    request,
) -> AsyncGenerator[DatabaseTaskStore, None]:
    """
    Fixture that provides a DatabaseTaskStore connected to different databases
    based on parameterization (SQLite, PostgreSQL, MySQL).
    """
    db_url, dialect_name = request.param

    if db_url is None:
        pytest.skip(f'DSN for {dialect_name} not set in environment variables.')

    # Ensure the path for file-based SQLite exists if that DSN is used
    # if "sqlite" in db_url and "memory" not in db_url:
    #     db_file_path = db_url.split("///")[-1]
    #     os.makedirs(os.path.dirname(db_file_path), exist_ok=True)

    engine = create_async_engine(db_url)
    store = None  # Initialize store to None for the finally block

    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # create_table=False as we've explicitly created tables above.
        store = DatabaseTaskStore(db_url, create_table=False)
        # Initialize the store (connects, etc.). Safe to call even if tables exist.
        await store.initialize()

        yield store

    finally:
        # Teardown
        if store:  # If store was successfully created
            await store.close()  # Closes the store's own engine

        if engine:  # If engine was created for setup/teardown
            # Drop tables using the fixture's engine
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()  # Dispose the engine created in the fixture


@pytest.mark.asyncio
async def test_initialize_creates_table(
    db_store_parameterized: DatabaseTaskStore,
) -> None:
    """Test that tables are created (implicitly by fixture setup)."""
    # Ensure store is initialized (already done by fixture, but good for clarity)
    await db_store_parameterized._ensure_initialized()

    # Use the store's engine for inspection
    async with db_store_parameterized.engine.connect() as conn:

        def has_table_sync(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.has_table(TaskModel.__tablename__)

        assert await conn.run_sync(has_table_sync)


@pytest.mark.asyncio
async def test_save_task(db_store_parameterized: DatabaseTaskStore) -> None:
    """Test saving a task to the DatabaseTaskStore."""
    task_to_save = MINIMAL_TASK_OBJ.model_copy(deep=True)
    # Ensure unique ID for parameterized tests if needed, or rely on table isolation
    task_to_save.id = (
        f'save-task-{db_store_parameterized.engine.url.drivername}'
    )
    await db_store_parameterized.save(task_to_save)

    retrieved_task = await db_store_parameterized.get(task_to_save.id)
    assert retrieved_task is not None
    assert retrieved_task.id == task_to_save.id
    assert retrieved_task.model_dump() == task_to_save.model_dump()
    await db_store_parameterized.delete(task_to_save.id)  # Cleanup


@pytest.mark.asyncio
async def test_get_task(db_store_parameterized: DatabaseTaskStore) -> None:
    """Test retrieving a task from the DatabaseTaskStore."""
    task_id = f'get-test-task-{db_store_parameterized.engine.url.drivername}'
    task_to_save = MINIMAL_TASK_OBJ.model_copy(update={'id': task_id})
    await db_store_parameterized.save(task_to_save)

    retrieved_task = await db_store_parameterized.get(task_to_save.id)
    assert retrieved_task is not None
    assert retrieved_task.id == task_to_save.id
    assert retrieved_task.contextId == task_to_save.contextId
    assert retrieved_task.status.state == TaskState.submitted
    await db_store_parameterized.delete(task_to_save.id)  # Cleanup


@pytest.mark.asyncio
async def test_get_nonexistent_task(
    db_store_parameterized: DatabaseTaskStore,
) -> None:
    """Test retrieving a nonexistent task."""
    retrieved_task = await db_store_parameterized.get('nonexistent-task-id')
    assert retrieved_task is None


@pytest.mark.asyncio
async def test_delete_task(db_store_parameterized: DatabaseTaskStore) -> None:
    """Test deleting a task from the DatabaseTaskStore."""
    task_id = f'delete-test-task-{db_store_parameterized.engine.url.drivername}'
    task_to_save_and_delete = MINIMAL_TASK_OBJ.model_copy(
        update={'id': task_id}
    )
    await db_store_parameterized.save(task_to_save_and_delete)

    assert (
        await db_store_parameterized.get(task_to_save_and_delete.id) is not None
    )
    await db_store_parameterized.delete(task_to_save_and_delete.id)
    assert await db_store_parameterized.get(task_to_save_and_delete.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_task(
    db_store_parameterized: DatabaseTaskStore,
) -> None:
    """Test deleting a nonexistent task. Should not error."""
    await db_store_parameterized.delete('nonexistent-delete-task-id')


@pytest.mark.asyncio
async def test_save_and_get_detailed_task(
    db_store_parameterized: DatabaseTaskStore,
) -> None:
    """Test saving and retrieving a task with more fields populated."""
    task_id = f'detailed-task-{db_store_parameterized.engine.url.drivername}'
    test_task = Task(
        id=task_id,
        contextId='test-session-1',
        status=TaskStatus(
            state=TaskState.working, timestamp='2023-01-01T12:00:00Z'
        ),
        kind='task',
        metadata={'key1': 'value1', 'key2': 123},
        artifacts=[
            Artifact(
                artifactId='artifact-1',
                parts=[Part(root=TextPart(text='hello'))],
            )
        ],
        history=[
            Message(
                messageId='msg-1',
                role=Role.user,
                parts=[Part(root=TextPart(text='user input'))],
            )
        ],
    )

    await db_store_parameterized.save(test_task)
    retrieved_task = await db_store_parameterized.get(test_task.id)

    assert retrieved_task is not None
    assert retrieved_task.id == test_task.id
    assert retrieved_task.contextId == test_task.contextId
    assert retrieved_task.status.state == TaskState.working
    assert retrieved_task.status.timestamp == '2023-01-01T12:00:00Z'
    assert retrieved_task.metadata == {'key1': 'value1', 'key2': 123}

    # Pydantic models handle their own serialization for comparison if model_dump is used
    assert (
        retrieved_task.model_dump()['artifacts']
        == test_task.model_dump()['artifacts']
    )
    assert (
        retrieved_task.model_dump()['history']
        == test_task.model_dump()['history']
    )

    await db_store_parameterized.delete(test_task.id)
    assert await db_store_parameterized.get(test_task.id) is None


@pytest.mark.asyncio
async def test_update_task(db_store_parameterized: DatabaseTaskStore) -> None:
    """Test updating an existing task."""
    task_id = f'update-test-task-{db_store_parameterized.engine.url.drivername}'
    original_task = Task(
        id=task_id,
        contextId='session-update',
        status=TaskStatus(
            state=TaskState.submitted, timestamp='2023-01-02T10:00:00Z'
        ),
        kind='task',
        metadata=None,  # Explicitly None
        artifacts=[],
        history=[],
    )
    await db_store_parameterized.save(original_task)

    retrieved_before_update = await db_store_parameterized.get(task_id)
    assert retrieved_before_update is not None
    assert retrieved_before_update.status.state == TaskState.submitted
    assert retrieved_before_update.metadata is None

    updated_task = original_task.model_copy(deep=True)
    updated_task.status.state = TaskState.completed
    updated_task.status.timestamp = '2023-01-02T11:00:00Z'
    updated_task.metadata = {'update_key': 'update_value'}

    await db_store_parameterized.save(updated_task)

    retrieved_after_update = await db_store_parameterized.get(task_id)
    assert retrieved_after_update is not None
    assert retrieved_after_update.status.state == TaskState.completed
    assert retrieved_after_update.metadata == {'update_key': 'update_value'}

    await db_store_parameterized.delete(task_id)


# Ensure aiosqlite, asyncpg, and aiomysql are installed in the test environment (added to pyproject.toml).
