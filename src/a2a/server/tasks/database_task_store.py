import logging


try:
    from sqlalchemy import delete, select, update
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
except ImportError as e:
    raise ImportError(
        'DatabaseTaskStore requires SQLAlchemy and a database driver. '
        'Install with one of: '
        "'pip install a2a-sdk[postgresql]', "
        "'pip install a2a-sdk[mysql]', "
        "'pip install a2a-sdk[sqlite]', "
        "or 'pip install a2a-sdk[sql]'"
    ) from e

from a2a.server.models import (  # TaskModel is our SQLAlchemy model
    Base,
    TaskModel,
)
from a2a.server.tasks.task_store import TaskStore
from a2a.types import Task  # Task is the Pydantic model


logger = logging.getLogger(__name__)


class DatabaseTaskStore(TaskStore):
    """SQLAlchemy-based implementation of TaskStore.

    Stores task objects in a database supported by SQLAlchemy.
    """

    engine: AsyncEngine
    async_session_maker: async_sessionmaker[AsyncSession]
    create_table: bool
    _initialized: bool

    def __init__(
        self,
        db_url: str,
        create_table: bool = True,
    ) -> None:
        """Initializes the DatabaseTaskStore.

        Args:
            db_url: Database connection string.
            create_table: If true, create tasks table on initialization.
        """
        logger.debug(f'Initializing DatabaseTaskStore with DB URL: {db_url}')
        self.engine = create_async_engine(
            db_url, echo=False
        )  # Set echo=True for SQL logging
        self.async_session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        self.create_table = create_table
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database and create the table if needed."""
        if self._initialized:
            return

        logger.debug('Initializing database schema...')
        if self.create_table:
            async with self.engine.begin() as conn:
                # This will create the 'tasks' table based on TaskModel's definition
                await conn.run_sync(Base.metadata.create_all)
        self._initialized = True
        logger.debug('Database schema initialized.')

    async def close(self) -> None:
        """Close the database connection engine."""
        if self.engine:
            logger.debug('Closing database engine.')
            await self.engine.dispose()
            self._initialized = False  # Reset initialization status

    async def _ensure_initialized(self) -> None:
        """Ensure the database connection is initialized."""
        if not self._initialized:
            await self.initialize()

    async def save(self, task: Task) -> None:
        """Saves or updates a task in the database."""
        await self._ensure_initialized()

        task_data = task.model_dump(
            mode='json'
        )  # Converts Pydantic Task to dict with JSON-serializable values

        async with self.async_session_maker.begin() as session:
            stmt_select = select(TaskModel).where(TaskModel.id == task.id)
            result = await session.execute(stmt_select)
            existing_task_model = result.scalar_one_or_none()

            if existing_task_model:
                logger.debug(f'Updating task {task.id} in the database.')
                update_data = {
                    'contextId': task_data['contextId'],
                    'kind': task_data['kind'],
                    'status': task_data[
                        'status'
                    ],  # Already a dict from model_dump
                    'artifacts': task_data.get(
                        'artifacts'
                    ),  # Already a list of dicts
                    'history': task_data.get(
                        'history'
                    ),  # Already a list of dicts
                    'task_metadata': task_data.get(
                        'metadata'
                    ),  # Already a dict
                }
                stmt_update = (
                    update(TaskModel)
                    .where(TaskModel.id == task.id)
                    .values(**update_data)
                )
                await session.execute(stmt_update)
            else:
                logger.debug(f'Saving new task {task.id} to the database.')
                # Map Pydantic fields to database columns
                new_task_model = TaskModel(
                    id=task_data['id'],
                    contextId=task_data['contextId'],
                    kind=task_data['kind'],
                    status=task_data['status'],
                    artifacts=task_data.get('artifacts'),
                    history=task_data.get('history'),
                    task_metadata=task_data.get(
                        'metadata'
                    ),  # Map metadata field to task_metadata column
                )
                session.add(new_task_model)
            # Commit is automatic when using session.begin()
        logger.info(f'Task {task.id} saved successfully.')

    async def get(self, task_id: str) -> Task | None:
        """Retrieves a task from the database by ID."""
        await self._ensure_initialized()

        async with self.async_session_maker() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()

            if task_model:
                # Map database columns to Pydantic model fields
                task_data_from_db = {
                    'id': task_model.id,
                    'contextId': task_model.contextId,
                    'kind': task_model.kind,
                    'status': task_model.status,
                    'artifacts': task_model.artifacts,
                    'history': task_model.history,
                    'metadata': task_model.task_metadata,  # Map task_metadata column to metadata field
                }
                # Pydantic's model_validate will parse the nested dicts/lists from JSON
                task = Task.model_validate(task_data_from_db)
                logger.debug(f'Task {task_id} retrieved successfully.')
                return task

            logger.debug(f'Task {task_id} not found in store.')
            return None

    async def delete(self, task_id: str) -> None:
        """Deletes a task from the database by ID."""
        await self._ensure_initialized()

        async with self.async_session_maker.begin() as session:
            stmt = delete(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            # Commit is automatic when using session.begin()

            if result.rowcount > 0:
                logger.info(f'Task {task_id} deleted successfully.')
            else:
                logger.warning(
                    f'Attempted to delete nonexistent task with id: {task_id}'
                )
